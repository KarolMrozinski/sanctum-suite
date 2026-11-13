using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Sockets;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Effects;
using System.Windows.Media.Imaging;
using System.Windows.Shapes;
using System.Windows.Threading;
using IO = System.IO;
using WinForms = System.Windows.Forms;
using Wpf = System.Windows;

namespace SanctumSuiteLauncher;

public partial class App : Wpf.Application
{
    private const string AppMutexName = "Global\\SanctumSuiteLauncher";
    private static readonly Mutex SingleInstanceMutex = new(false, AppMutexName);
    private readonly string _root = ResolveRepoRoot();
    private readonly string _appDir = IO.Path.Combine(ResolveRepoRoot(), "sanctum-dashboard");
    private readonly string _pidFile = IO.Path.Combine(ResolveRepoRoot(), ".sanctum-suite.pid");
    private readonly string _browserFlag = IO.Path.Combine(ResolveRepoRoot(), ".sanctum-suite.browser-opened");
    private readonly string _runtimeLogFile = IO.Path.Combine(ResolveRepoRoot(), ".sanctum-suite.runtime.log");
    private readonly HttpClient _client = new();
    private readonly object _startupLock = new();
    private bool _startupInProgress;
    private string AppUrl => NormalizeAppUrl(Environment.GetEnvironmentVariable("SANCTUM_APP_URL") ?? "http://127.0.0.1:3000");
    private Wpf.Window _window = null!;
    private readonly DispatcherTimer _timer = new();
    private Process? _nodeProcess;
    private Wpf.Controls.Button _startBtn = null!;
    private Wpf.Controls.Button _stopBtn = null!;
    private Wpf.Controls.Button _killStaleBtn = null!;
    private Wpf.Controls.Button _openBtn = null!;
    private Wpf.Controls.TextBlock _status = null!;
    private Wpf.Controls.TextBlock _statusDetail = null!;
    private Wpf.Controls.TextBox _logViewer = null!;
    private Wpf.Controls.TextBlock _envSummary = null!;
    private Border _statusDot = null!;
    private Border _loadingRing = null!;
    private Wpf.Controls.TextBlock _loadingLabel = null!;
    private Wpf.Controls.TextBlock _runtimeSummary = null!;
    private WinForms.NotifyIcon? _trayIcon;
    private bool _isWindowVisible = true;

    private static ControlTemplate CreateFlatButtonTemplate(System.Windows.Media.Color baseColor)
    {
        var normalBrush = new SolidColorBrush(baseColor);
        var overBrush = new SolidColorBrush(System.Windows.Media.Color.FromArgb(255, (byte)Math.Min(baseColor.R + 18, 255), (byte)Math.Min(baseColor.G + 18, 255), (byte)Math.Min(baseColor.B + 18, 255)));
        var pressedBrush = new SolidColorBrush(System.Windows.Media.Color.FromArgb(255, (byte)Math.Max(baseColor.R - 20, 0), (byte)Math.Max(baseColor.G - 20, 0), (byte)Math.Max(baseColor.B - 20, 0)));

        var border = new FrameworkElementFactory(typeof(Border));
        border.SetValue(Border.CornerRadiusProperty, new CornerRadius(12));
        border.SetValue(Border.BackgroundProperty, normalBrush);
        border.SetValue(Border.BorderBrushProperty, System.Windows.Media.Brushes.Transparent);
        border.SetValue(Border.BorderThicknessProperty, new Thickness(0));
        border.SetValue(Border.SnapsToDevicePixelsProperty, true);

        var text = new FrameworkElementFactory(typeof(TextBlock));
        text.SetValue(TextBlock.TextProperty, new TemplateBindingExtension(ContentControl.ContentProperty));
        text.SetValue(TextBlock.HorizontalAlignmentProperty, Wpf.HorizontalAlignment.Center);
        text.SetValue(TextBlock.VerticalAlignmentProperty, VerticalAlignment.Center);
        text.SetValue(TextBlock.ForegroundProperty, new TemplateBindingExtension(Wpf.Controls.Control.ForegroundProperty));
        text.SetValue(TextBlock.FontWeightProperty, new TemplateBindingExtension(Wpf.Controls.Control.FontWeightProperty));
        text.SetValue(TextBlock.TextTrimmingProperty, TextTrimming.CharacterEllipsis);

        var panel = new FrameworkElementFactory(typeof(Grid));
        panel.AppendChild(text);

        border.AppendChild(panel);

        var template = new ControlTemplate(typeof(Wpf.Controls.Button));
        template.VisualTree = border;

        var triggerNormal = new Trigger
        {
            Property = UIElement.IsMouseOverProperty,
            Value = true
        };
        triggerNormal.Setters.Add(new Setter(Border.BackgroundProperty, overBrush, string.Empty));

        var triggerPressed = new Trigger
        {
            Property = Wpf.Controls.Primitives.ButtonBase.IsPressedProperty,
            Value = true
        };
        triggerPressed.Setters.Add(new Setter(Border.BackgroundProperty, pressedBrush, string.Empty));

        template.Triggers.Add(triggerNormal);
        template.Triggers.Add(triggerPressed);

        return template;
    }

    private static string ResolveRepoRoot()
    {
        var baseDir = AppDomain.CurrentDomain.BaseDirectory;
        var current = baseDir;

        for (var i = 0; i < 18; i++)
        {
            if (Directory.Exists(current) && File.Exists(IO.Path.Combine(current, "sanctum-dashboard", "package.json")))
            {
                return current;
            }

            var parent = Directory.GetParent(current);
            if (parent == null)
            {
                break;
            }

            current = parent.FullName;
        }

        var currentDirectory = Directory.GetCurrentDirectory();
        if (Directory.Exists(currentDirectory) && File.Exists(IO.Path.Combine(currentDirectory, "sanctum-dashboard", "package.json")))
        {
            return currentDirectory;
        }

        return baseDir;
    }

    private static string NormalizeAppUrl(string? value)
    {
        var candidate = string.IsNullOrWhiteSpace(value) ? "http://127.0.0.1:3000" : value.Trim();
        if (candidate.EndsWith("/", StringComparison.Ordinal) && candidate.Length > 1)
        {
            candidate = candidate.TrimEnd('/');
        }

        candidate = candidate.Replace("0.0.0.0", "127.0.0.1", StringComparison.OrdinalIgnoreCase);
        if (!Uri.TryCreate(candidate, UriKind.Absolute, out var uri))
        {
            return "http://127.0.0.1:3000";
        }

        return uri.GetLeftPart(UriPartial.Authority).TrimEnd('/') + (string.IsNullOrEmpty(uri.AbsolutePath) || uri.AbsolutePath == "/" ? string.Empty : uri.AbsolutePath);
    }

    private static bool IsAppHealthy(string url)
    {
        try
        {
            using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(2) };
            using var response = client.GetAsync(url).GetAwaiter().GetResult();
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    private void CleanupStaleSanctumProcesses()
    {
        foreach (var proc in Process.GetProcesses().Where(p =>
                     p.ProcessName.Contains("node", StringComparison.OrdinalIgnoreCase)
                     || p.ProcessName.Contains("powershell", StringComparison.OrdinalIgnoreCase)
                     || p.ProcessName.Contains("cmd", StringComparison.OrdinalIgnoreCase)).ToList())
        {
            try
            {
                var cmd = proc.StartInfo?.Arguments ?? string.Empty;
                var matchesSanctum = cmd.Contains("sanctum-dashboard", StringComparison.OrdinalIgnoreCase)
                    || cmd.Contains("next dev", StringComparison.OrdinalIgnoreCase)
                    || cmd.Contains("npm run dev", StringComparison.OrdinalIgnoreCase)
                    || cmd.Contains("--port 3000", StringComparison.OrdinalIgnoreCase)
                    || cmd.Contains("--hostname", StringComparison.OrdinalIgnoreCase);

                if (matchesSanctum && !IsAppHealthy(AppUrl))
                {
                    proc.Kill(true);
                    AppendLog($"[launcher] Killed stale Sanctum dev process PID {proc.Id}.");
                }
            }
            catch { }
        }
    }

    protected override void OnExit(ExitEventArgs e)
    {
        try
        {
            SingleInstanceMutex.ReleaseMutex();
        }
        catch
        {
        }

        base.OnExit(e);
    }

    protected override void OnStartup(StartupEventArgs e)
    {
        if (!Directory.Exists(_appDir) || !File.Exists(IO.Path.Combine(_appDir, "package.json")))
        {
            _status = new TextBlock { Text = "Status: repo missing", Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(248, 113, 113)) };
            var message = $"Sanctum Dashboard was not found under the expected repo path. Expected: {_appDir}\n\nPlease run the launcher from the Sanctum Suite repo root or make sure the app folder is present.";
            Wpf.MessageBox.Show(message, "Sanctum Suite", MessageBoxButton.OK, MessageBoxImage.Error);
            Shutdown();
            return;
        }

        try
        {
            File.WriteAllText(_runtimeLogFile, string.Empty);
        }
        catch { }

        _window = new Window
        {
            Title = "Sanctum Suite",
            Width = 620,
            Height = 420,
            MinWidth = 520,
            MinHeight = 340,
            WindowStartupLocation = WindowStartupLocation.CenterScreen,
            ResizeMode = ResizeMode.NoResize,
            WindowStyle = WindowStyle.None,
            AllowsTransparency = true,
            Background = Wpf.Media.Brushes.Transparent,
            Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(226, 232, 240)),
            Icon = new BitmapImage(new Uri(IO.Path.Combine(_root, "resources", "sanctum-suite-icon.ico"), UriKind.Absolute)),
            ShowInTaskbar = true,
            Topmost = false
        };

        _window.MouseLeftButtonDown += (_, _) => _window.DragMove();

        var shadow = new DropShadowEffect
        {
            Color = System.Windows.Media.Color.FromArgb(160, 15, 23, 42),
            BlurRadius = 30,
            ShadowDepth = 18,
            Opacity = 0.85
        };

        var outer = new Border
        {
            CornerRadius = new CornerRadius(24),
            BorderBrush = new SolidColorBrush(System.Windows.Media.Color.FromArgb(120, 148, 163, 184)),
            BorderThickness = new Thickness(1.2),
            Background = new LinearGradientBrush(
                System.Windows.Media.Color.FromArgb(230, 7, 13, 22),
                System.Windows.Media.Color.FromArgb(220, 12, 20, 30),
                90),
            Padding = new Thickness(20),
            Margin = new Thickness(12),
            Effect = shadow
        };

        var rootGrid = new Grid();
        rootGrid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        rootGrid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        rootGrid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        rootGrid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        rootGrid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

        var header = new Grid { Margin = new Thickness(0, 0, 0, 12) };
        header.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        header.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        header.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

        var iconBorder = new Border
        {
            Width = 34,
            Height = 34,
            CornerRadius = new CornerRadius(11),
            Background = new LinearGradientBrush(
                System.Windows.Media.Color.FromRgb(45, 212, 191),
                System.Windows.Media.Color.FromRgb(14, 116, 144),
                90),
            Margin = new Thickness(0, 0, 12, 0),
            BorderBrush = new SolidColorBrush(System.Windows.Media.Color.FromArgb(90, 148, 163, 184)),
            BorderThickness = new Thickness(1),
            Child = new TextBlock
            {
                Text = "S",
                FontSize = 18,
                FontWeight = FontWeights.Bold,
                HorizontalAlignment = Wpf.HorizontalAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center,
                Foreground = Wpf.Media.Brushes.White
            }
        };
        header.Children.Add(iconBorder);

        var title = new TextBlock
        {
            Text = "Sanctum Suite",
            FontSize = 25,
            FontWeight = FontWeights.Bold,
            Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(131, 224, 196)),
            VerticalAlignment = VerticalAlignment.Center
        };
        Grid.SetColumn(title, 1);
        header.Children.Add(title);

        _statusDot = new Border
        {
            Width = 11,
            Height = 11,
            CornerRadius = new CornerRadius(6),
            Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(100, 116, 139)),
            Margin = new Thickness(0, 0, 8, 0),
            VerticalAlignment = VerticalAlignment.Center
        };
        Grid.SetColumn(_statusDot, 2);
        header.Children.Add(_statusDot);

        var closeBtn = new Wpf.Controls.Button
        {
            Content = "✕",
            Width = 30,
            Height = 30,
            Background = new SolidColorBrush(System.Windows.Media.Color.FromArgb(80, 148, 163, 184)),
            Foreground = System.Windows.Media.Brushes.White,
            BorderThickness = new Thickness(0),
            Padding = new Thickness(0),
            ToolTip = "Zwin do zasobnika",
            Cursor = Wpf.Input.Cursors.Hand
        };
        closeBtn.Click += (_, _) => MinimizeToTray();
        Grid.SetColumn(closeBtn, 2);
        header.Children.Add(closeBtn);

        _status = new TextBlock
        {
            Text = "Status: ready",
            FontSize = 16,
            FontWeight = FontWeights.SemiBold,
            Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(226, 232, 240)),
            Margin = new Thickness(0, 0, 0, 6)
        };

        _statusDetail = new TextBlock
        {
            Text = "Checking environment and startup status...",
            FontSize = 12,
            Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(148, 163, 184)),
            Margin = new Thickness(0, 0, 0, 12)
        };

        var topSummary = new Grid { Margin = new Thickness(0, 0, 0, 12) };
        topSummary.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        topSummary.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

        var loadingDot = new Ellipse
        {
            Width = 8,
            Height = 8,
            Fill = new SolidColorBrush(System.Windows.Media.Color.FromRgb(45, 212, 191)),
            HorizontalAlignment = Wpf.HorizontalAlignment.Center,
            VerticalAlignment = VerticalAlignment.Center,
            RenderTransformOrigin = new Wpf.Point(0.5, 0.5)
        };

        var loadingSpin = new RotateTransform();
        loadingDot.RenderTransform = loadingSpin;

        var spinAnimation = new DoubleAnimation
        {
            From = 0,
            To = 360,
            Duration = TimeSpan.FromSeconds(1.6),
            RepeatBehavior = RepeatBehavior.Forever,
            AutoReverse = false
        };
        loadingSpin.BeginAnimation(RotateTransform.AngleProperty, spinAnimation);

        _loadingRing = new Border
        {
            Width = 28,
            Height = 28,
            CornerRadius = new CornerRadius(14),
            BorderBrush = new SolidColorBrush(System.Windows.Media.Color.FromArgb(140, 45, 212, 191)),
            BorderThickness = new Thickness(2.1),
            Margin = new Thickness(0, 0, 10, 0),
            Background = new SolidColorBrush(System.Windows.Media.Color.FromArgb(26, 45, 212, 191)),
            Child = loadingDot,
            SnapsToDevicePixels = true,
            UseLayoutRounding = true
        };

        _loadingLabel = new Wpf.Controls.TextBlock
        {
            Text = "System ready",
            FontSize = 11,
            Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(191, 219, 254)),
            FontWeight = FontWeights.SemiBold,
            VerticalAlignment = VerticalAlignment.Center,
            Visibility = Visibility.Visible
        };

        Grid.SetColumn(_loadingRing, 0);
        Grid.SetColumn(_loadingLabel, 1);
        topSummary.Children.Add(_loadingRing);
        topSummary.Children.Add(_loadingLabel);

        var envPanel = new Border
        {
            Background = new LinearGradientBrush(
                System.Windows.Media.Color.FromArgb(80, 34, 197, 94),
                System.Windows.Media.Color.FromArgb(65, 12, 74, 110),
                90),
            Padding = new Thickness(16, 11, 16, 11),
            CornerRadius = new CornerRadius(12),
            Margin = new Thickness(0, 0, 0, 12),
            BorderBrush = new SolidColorBrush(System.Windows.Media.Color.FromArgb(80, 94, 234, 212)),
            BorderThickness = new Thickness(1)
        };
        _envSummary = new TextBlock
        {
            Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(191, 219, 254)),
            FontSize = 12,
            FontWeight = FontWeights.SemiBold,
            Text = "Node: checking • npm: checking • port 3000: checking"
        };
        envPanel.Child = _envSummary;

        _runtimeSummary = new Wpf.Controls.TextBlock
        {
            Text = "Runtime: waiting for process health",
            Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(148, 163, 184)),
            FontSize = 11,
            Margin = new Thickness(0, 0, 0, 8)
        };

        _logViewer = new Wpf.Controls.TextBox
        {
            Height = 122,
            IsReadOnly = true,
            TextWrapping = TextWrapping.Wrap,
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            Background = new SolidColorBrush(System.Windows.Media.Color.FromArgb(255, 8, 15, 24)),
            BorderBrush = new SolidColorBrush(System.Windows.Media.Color.FromArgb(120, 94, 234, 212)),
            BorderThickness = new Thickness(1),
            Padding = new Thickness(10, 8, 10, 8),
            Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(191, 219, 254)),
            FontFamily = new System.Windows.Media.FontFamily("Consolas"),
            FontSize = 11,
            Margin = new Thickness(0, 0, 0, 12),
            Text = "[launcher] Preparing startup diagnostics...",
            CaretBrush = System.Windows.Media.Brushes.White
        };

        var buttons = new Grid();
        buttons.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        buttons.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        buttons.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        buttons.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1.15, GridUnitType.Star) });

        _startBtn = new Wpf.Controls.Button
        {
            Content = "Start",
            Height = 46,
            Margin = new Thickness(0, 0, 8, 0),
            Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(14, 116, 144)),
            Foreground = System.Windows.Media.Brushes.White,
            BorderBrush = System.Windows.Media.Brushes.Transparent,
            BorderThickness = new Thickness(0),
            FontWeight = FontWeights.SemiBold,
            Cursor = System.Windows.Input.Cursors.Hand,
            Padding = new Thickness(0),
            HorizontalAlignment = Wpf.HorizontalAlignment.Stretch,
            VerticalContentAlignment = VerticalAlignment.Center,
            HorizontalContentAlignment = Wpf.HorizontalAlignment.Center,
            FocusVisualStyle = null,
            SnapsToDevicePixels = true,
            UseLayoutRounding = true,
            Template = CreateFlatButtonTemplate(System.Windows.Media.Color.FromRgb(14, 116, 144))
        };

        _stopBtn = new Wpf.Controls.Button
        {
            Content = "Stop",
            Height = 46,
            Margin = new Thickness(8, 0, 8, 0),
            Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(51, 65, 85)),
            Foreground = System.Windows.Media.Brushes.White,
            BorderBrush = System.Windows.Media.Brushes.Transparent,
            BorderThickness = new Thickness(0),
            FontWeight = FontWeights.SemiBold,
            Cursor = System.Windows.Input.Cursors.Hand,
            Padding = new Thickness(0),
            HorizontalAlignment = Wpf.HorizontalAlignment.Stretch,
            VerticalContentAlignment = VerticalAlignment.Center,
            HorizontalContentAlignment = Wpf.HorizontalAlignment.Center,
            FocusVisualStyle = null,
            SnapsToDevicePixels = true,
            UseLayoutRounding = true,
            Template = CreateFlatButtonTemplate(System.Windows.Media.Color.FromRgb(51, 65, 85))
        };

        _killStaleBtn = new Wpf.Controls.Button
        {
            Content = "Kill stale server",
            Height = 46,
            Margin = new Thickness(8, 0, 8, 0),
            Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(120, 53, 15)),
            Foreground = System.Windows.Media.Brushes.White,
            BorderBrush = System.Windows.Media.Brushes.Transparent,
            BorderThickness = new Thickness(0),
            FontWeight = FontWeights.SemiBold,
            Cursor = System.Windows.Input.Cursors.Hand,
            Padding = new Thickness(0),
            HorizontalAlignment = Wpf.HorizontalAlignment.Stretch,
            VerticalContentAlignment = VerticalAlignment.Center,
            HorizontalContentAlignment = Wpf.HorizontalAlignment.Center,
            FocusVisualStyle = null,
            SnapsToDevicePixels = true,
            UseLayoutRounding = true,
            Template = CreateFlatButtonTemplate(System.Windows.Media.Color.FromRgb(120, 53, 15))
        };

        _openBtn = new Wpf.Controls.Button
        {
            Content = "Open app",
            Height = 46,
            Margin = new Thickness(8, 0, 0, 0),
            Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(24, 24, 27)),
            Foreground = System.Windows.Media.Brushes.White,
            BorderBrush = System.Windows.Media.Brushes.Transparent,
            BorderThickness = new Thickness(0),
            FontWeight = FontWeights.SemiBold,
            Cursor = System.Windows.Input.Cursors.Hand,
            Padding = new Thickness(0),
            HorizontalAlignment = Wpf.HorizontalAlignment.Stretch,
            VerticalContentAlignment = VerticalAlignment.Center,
            HorizontalContentAlignment = Wpf.HorizontalAlignment.Center,
            FocusVisualStyle = null,
            SnapsToDevicePixels = true,
            UseLayoutRounding = true,
            Template = CreateFlatButtonTemplate(System.Windows.Media.Color.FromRgb(24, 24, 27))
        };

        Grid.SetColumn(_startBtn, 0);
        Grid.SetColumn(_stopBtn, 1);
        Grid.SetColumn(_killStaleBtn, 2);
        Grid.SetColumn(_openBtn, 3);

        _startBtn.Click += async (_, _) => await StartAppAsync();
        _stopBtn.Click += (_, _) => StopApp();
        _killStaleBtn.Click += (_, _) => KillStaleNodeServer();
        _openBtn.Click += (_, _) =>
        {
            if (!IsAppRunning()) return;
            TryOpenBrowser(false);
        };

        buttons.Children.Add(_startBtn);
        buttons.Children.Add(_stopBtn);
        buttons.Children.Add(_killStaleBtn);
        buttons.Children.Add(_openBtn);

        Grid.SetRow(header, 0);
        Grid.SetRow(_status, 1);
        Grid.SetRow(_statusDetail, 2);
        Grid.SetRow(envPanel, 3);
        Grid.SetRow(_logViewer, 4);
        Grid.SetRow(buttons, 5);

        rootGrid.Children.Add(header);
        rootGrid.Children.Add(_status);
        rootGrid.Children.Add(_statusDetail);
        rootGrid.Children.Add(envPanel);
        rootGrid.Children.Add(_logViewer);
        rootGrid.Children.Add(buttons);

        outer.Child = rootGrid;
        _window.Content = outer;

        _trayIcon = new WinForms.NotifyIcon
        {
            Visible = true,
            Icon = new Icon(IO.Path.Combine(_root, "resources", "sanctum-suite-icon.ico")),
            Text = "Sanctum Suite"
        };
        _trayIcon.Click += (_, _) =>
        {
            if (_isWindowVisible)
            {
                MinimizeToTray();
            }
            else
            {
                RestoreWindow();
            }
        };

        var trayMenu = new WinForms.ContextMenuStrip();
        var startItem = new WinForms.ToolStripMenuItem("Start");
        startItem.Click += async (_, _) => await StartAppAsync();

        var stopItem = new WinForms.ToolStripMenuItem("Stop");
        stopItem.Click += (_, _) => StopApp();

        var killStaleItem = new WinForms.ToolStripMenuItem("Kill stale server");
        killStaleItem.Click += (_, _) => KillStaleNodeServer();

        var showItem = new WinForms.ToolStripMenuItem("Show");
        showItem.Click += (_, _) => RestoreWindow();

        var openItem = new WinForms.ToolStripMenuItem("Open app");
        openItem.Click += (_, _) =>
        {
            if (IsAppRunning())
            {
                TryOpenBrowser(false);
            }
        };

        var exitItem = new WinForms.ToolStripMenuItem("Exit");
        exitItem.Click += (_, _) =>
        {
            StopApp(false);
            _trayIcon.Visible = false;
            _window.Close();
        };

        trayMenu.Items.Add(startItem);
        trayMenu.Items.Add(stopItem);
        trayMenu.Items.Add(killStaleItem);
        trayMenu.Items.Add(new ToolStripSeparator());
        trayMenu.Items.Add(showItem);
        trayMenu.Items.Add(openItem);
        trayMenu.Items.Add(new ToolStripSeparator());
        trayMenu.Items.Add(exitItem);
        _trayIcon.ContextMenuStrip = trayMenu;

        _timer.Interval = TimeSpan.FromSeconds(1);
        _timer.Tick += (_, _) => RefreshStatus();
        _timer.Start();

        _window.Show();
        _window.Activate();
        AppendLog("[launcher] Startup diagnostics initialized. Automatic app launch is disabled until user starts it manually.");
        RefreshStatus();

        base.OnStartup(e);
    }

    private async Task StartAppAsync()
    {
        lock (_startupLock)
        {
            if (_startupInProgress)
            {
                return;
            }

            _startupInProgress = true;
        }

        try
        {
            var appProjectDir = _appDir;

            CleanupStaleSanctumProcesses();

            if (IsAppRunning())
            {
                SetStatus("Running", true, $"Dashboard is already responding on {AppUrl}");
                AppendLog($"[launcher] App already running; skipping startup ({AppUrl})");
                return;
            }

            if (!Directory.Exists(appProjectDir) || !File.Exists(IO.Path.Combine(appProjectDir, "package.json")))
            {
                SetStatus("Project missing", false, "Unable to locate sanctum-dashboard folder");
                AppendLog($"[launcher] Missing project folder: {appProjectDir}");
                return;
            }

            var envIssues = ValidateEnvironment();
            if (envIssues.Count > 0)
            {
                var first = envIssues[0];
                SetStatus("Environment issue", false, first);
                AppendLog($"[launcher] Environment check failed: {first}");
                return;
            }

            if (!File.Exists(IO.Path.Combine(appProjectDir, "node_modules", "next", "package.json")))
            {
                SetStatus("Installing dependencies", false, "npm install is running for the dashboard");
                AppendLog("[launcher] Dependencies missing; installing npm packages...");
                var install = Process.Start(new ProcessStartInfo("cmd.exe", $"/c cd /d \"{appProjectDir}\" && npm install --no-fund --no-audit")
                {
                    UseShellExecute = true,
                    CreateNoWindow = false
                });
                if (install != null)
                {
                    install.WaitForExit();
                }
            }

            StopApp(false);
            try { File.Delete(_browserFlag); } catch { }

            var port = ExtractPort(AppUrl);
            var host = ExtractHost(AppUrl);
            var command = $"Set-Location '{appProjectDir}'; npm run dev -- --hostname {host} --port {port}";
            var startInfo = new ProcessStartInfo
            {
                FileName = "powershell.exe",
                Arguments = $"-NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command \"{command}\"",
                WorkingDirectory = appProjectDir,
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
            };

            _nodeProcess = Process.Start(startInfo);
            if (_nodeProcess != null)
            {
                _nodeProcess.OutputDataReceived += (_, args) =>
                {
                    if (!string.IsNullOrEmpty(args.Data))
                    {
                        AppendLog($"[node] {args.Data}");
                    }
                };

                _nodeProcess.ErrorDataReceived += (_, args) =>
                {
                    if (!string.IsNullOrEmpty(args.Data))
                    {
                        AppendLog($"[node:error] {args.Data}");
                    }
                };

                _nodeProcess.BeginOutputReadLine();
                _nodeProcess.BeginErrorReadLine();
                File.WriteAllText(_pidFile, _nodeProcess.Id.ToString());
            }

            SetStatus("Starting", false, "Launching Next.js dashboard and waiting for health check");
            AppendLog($"[launcher] Starting dashboard in {appProjectDir} on {AppUrl}");

            var started = false;
            for (var i = 0; i < 120; i++)
            {
                try
                {
                    using var resp = await _client.GetAsync(AppUrl, HttpCompletionOption.ResponseHeadersRead);
                    if (resp.IsSuccessStatusCode)
                    {
                        started = true;
                        break;
                    }
                }
                catch { }

                if (_nodeProcess is { HasExited: true })
                {
                    AppendLog("[launcher] Node process exited before the app became healthy.");
                    break;
                }

                await Task.Delay(1000);
            }

            if (started)
            {
                SetStatus("Running", true, "Dashboard is live and responding on localhost:3000");
                AppendLog("[launcher] Dashboard health check passed. Browser launch is deferred until the user clicks Open app.");
            }
            else
            {
                SetStatus("Startup failed", false, "Dashboard did not respond before the timeout window");
                AppendLog("[launcher] Startup timeout reached; app did not respond on the expected URL.");
            }

            RefreshStatus();
        }
        catch (Exception ex)
        {
            SetStatus("Error", false, ex.Message);
            AppendLog($"[launcher] Startup exception: {ex.Message}");
            Wpf.MessageBox.Show(ex.Message, "Sanctum Suite");
        }
        finally
        {
            lock (_startupLock)
            {
                _startupInProgress = false;
            }
        }
    }

    private void TryOpenBrowser(bool remember = true)
    {
        if (!IsAppRunning())
        {
            return;
        }

        if (remember && File.Exists(_browserFlag))
        {
            return;
        }

        try
        {
            Process.Start(new ProcessStartInfo(AppUrl) { UseShellExecute = true });
        }
        catch
        {
            try
            {
                Process.Start(new ProcessStartInfo("cmd.exe", $"/c start \"\" \"{AppUrl}\"") { UseShellExecute = true });
            }
            catch
            {
                return;
            }
        }

        if (remember)
        {
            try
            {
                File.WriteAllText(_browserFlag, DateTime.UtcNow.ToString("O"));
            }
            catch { }
        }
    }

    private static bool IsLikelyDevServer(string? commandLine)
    {
        if (string.IsNullOrWhiteSpace(commandLine))
        {
            return false;
        }

        return commandLine.Contains("next dev", StringComparison.OrdinalIgnoreCase)
            || commandLine.Contains("npm run dev", StringComparison.OrdinalIgnoreCase)
            || commandLine.Contains("sanctum-dashboard", StringComparison.OrdinalIgnoreCase)
            || commandLine.Contains("--hostname", StringComparison.OrdinalIgnoreCase);
    }

    private static string ExtractHost(string url)
    {
        if (Uri.TryCreate(url, UriKind.Absolute, out var uri))
        {
            return uri.Host;
        }

        return "localhost";
    }

    private static int ExtractPort(string url)
    {
        if (Uri.TryCreate(url, UriKind.Absolute, out var uri) && uri.Port > 0)
        {
            return uri.Port;
        }

        return 3000;
    }

    private void AppendLog(string message)
    {
        try
        {
            var timestamp = DateTime.Now.ToString("HH:mm:ss");
            var line = $"[{timestamp}] {message}";
            File.AppendAllText(_runtimeLogFile, line + Environment.NewLine);

            if (_logViewer != null)
            {
                _logViewer.Dispatcher.Invoke(() =>
                {
                    var current = _logViewer.Text;
                    if (string.IsNullOrEmpty(current) || current == "[launcher] Preparing startup diagnostics...")
                    {
                        _logViewer.Text = line;
                    }
                    else
                    {
                        _logViewer.Text = current + Environment.NewLine + line;
                    }

                    _logViewer.ScrollToEnd();
                });
            }
        }
        catch { }
    }

    private List<string> ValidateEnvironment()
    {
        var issues = new List<string>();

        if (!TryResolveExecutable("node", out var nodePath))
        {
            issues.Add("Node.js is not available in PATH.");
        }
        else
        {
            AppendLog($"[launcher] Node resolved: {nodePath}");
        }

        if (!TryResolveExecutable("npm", out var npmPath))
        {
            issues.Add("npm is not available in PATH.");
        }
        else
        {
            AppendLog($"[launcher] npm resolved: {npmPath}");
        }

        var port = ExtractPort(AppUrl);
        if (IsPortInUse(port))
        {
            var appRunning = IsAppRunning();
            if (!appRunning)
            {
                issues.Add($"Port {port} jest zajęty przez stary proces Node. Zamknąć i uruchomić ponownie?");
            }
        }

        var envStatus = new StringBuilder();
        envStatus.Append(TryResolveExecutable("node", out _) ? "Node: OK" : "Node: missing");
        envStatus.Append(" • ");
        envStatus.Append(TryResolveExecutable("npm", out _) ? "npm: OK" : "npm: missing");
        envStatus.Append(" • ");
        envStatus.Append(IsPortInUse(ExtractPort(AppUrl)) ? "port 3000: busy" : "port 3000: free");
        _envSummary.Text = envStatus.ToString();

        return issues;
    }

    private static bool TryResolveExecutable(string fileName, out string path)
    {
        path = string.Empty;

        var pathVariable = Environment.GetEnvironmentVariable("PATH") ?? string.Empty;
        foreach (var entry in pathVariable.Split(';', StringSplitOptions.RemoveEmptyEntries))
        {
            var fullPath = IO.Path.Combine(entry, fileName);
            if (File.Exists(fullPath))
            {
                path = fullPath;
                return true;
            }

            var cmdPath = IO.Path.Combine(entry, fileName + ".cmd");
            if (File.Exists(cmdPath))
            {
                path = cmdPath;
                return true;
            }
        }

        return false;
    }

    private static bool IsPortInUse(int port)
    {
        try
        {
            using var listener = new TcpListener(IPAddress.Loopback, port);
            listener.Start();
            return false;
        }
        catch
        {
            return true;
        }
    }

    private void KillStaleNodeServer()
    {
        var killedAny = false;

        foreach (var proc in Process.GetProcesses().Where(p =>
                     p.ProcessName.Contains("node", StringComparison.OrdinalIgnoreCase)
                     || p.ProcessName.Contains("powershell", StringComparison.OrdinalIgnoreCase)
                     || p.ProcessName.Contains("cmd", StringComparison.OrdinalIgnoreCase)).ToList())
        {
            try
            {
                var cmd = proc.StartInfo?.Arguments ?? string.Empty;
                var isSanctumDev = cmd.Contains("sanctum-dashboard", StringComparison.OrdinalIgnoreCase)
                    || cmd.Contains("next dev", StringComparison.OrdinalIgnoreCase)
                    || cmd.Contains("npm run dev", StringComparison.OrdinalIgnoreCase)
                    || cmd.Contains("--hostname", StringComparison.OrdinalIgnoreCase)
                    || cmd.Contains("--port 3000", StringComparison.OrdinalIgnoreCase)
                    || cmd.Contains("3000", StringComparison.OrdinalIgnoreCase);

                if (!isSanctumDev)
                {
                    continue;
                }

                proc.Kill(true);
                killedAny = true;
                AppendLog($"[launcher] Killed stale Node server PID {proc.Id} on port 3000.");
            }
            catch { }
        }

        if (!killedAny)
        {
            AppendLog("[launcher] No stale Sanctum Node process was found to kill.");
        }

        try
        {
            File.Delete(_pidFile);
        }
        catch { }

        try
        {
            File.Delete(_browserFlag);
        }
        catch { }

        SetStatus("ready", true, "Port 3000 is free again. You can start the dashboard.");
        RefreshStatus();
    }

    private void OpenBrowserOnce()
    {
        TryOpenBrowser(true);
    }

    private bool IsAppRunning()
    {
        var targetUrl = AppUrl;

        if (IsAppHealthy(targetUrl))
        {
            return true;
        }

        var expectedHost = ExtractHost(targetUrl);
        var expectedPort = ExtractPort(targetUrl);

        if (File.Exists(_pidFile))
        {
            var value = File.ReadAllText(_pidFile).Trim();
            if (int.TryParse(value, out var pid))
            {
                try
                {
                    using var proc = Process.GetProcessById(pid);
                    if (!proc.HasExited)
                    {
                        return IsAppHealthy(targetUrl);
                    }
                }
                catch { }
            }
        }

        foreach (var proc in Process.GetProcesses())
        {
            try
            {
                var cmd = proc.StartInfo?.Arguments ?? string.Empty;
                var processName = proc.ProcessName ?? string.Empty;
                var isNodeOrShell = processName.Contains("node", StringComparison.OrdinalIgnoreCase)
                    || processName.Contains("powershell", StringComparison.OrdinalIgnoreCase)
                    || processName.Contains("cmd", StringComparison.OrdinalIgnoreCase);

                var matchesDevServer = IsLikelyDevServer(cmd);
                var matchesTargetUrl = cmd.Contains(expectedHost, StringComparison.OrdinalIgnoreCase)
                    || cmd.Contains($"--port {expectedPort}", StringComparison.OrdinalIgnoreCase)
                    || cmd.Contains("sanctum-dashboard", StringComparison.OrdinalIgnoreCase)
                    || cmd.Contains("next", StringComparison.OrdinalIgnoreCase);

                if (isNodeOrShell && (matchesDevServer || matchesTargetUrl))
                {
                    return IsAppHealthy(targetUrl);
                }
            }
            catch { }
        }

        return false;
    }

    private void SetStatus(string title, bool isHealthy, string detail)
    {
        _status.Text = $"Status: {title}";
        _status.Foreground = new SolidColorBrush(isHealthy ? System.Windows.Media.Color.FromRgb(127, 247, 211) : System.Windows.Media.Color.FromRgb(248, 113, 113));
        _statusDetail.Text = detail;
        _statusDetail.Foreground = new SolidColorBrush(isHealthy ? System.Windows.Media.Color.FromRgb(134, 239, 172) : System.Windows.Media.Color.FromRgb(254, 202, 202));
        _statusDot.Background = new SolidColorBrush(isHealthy ? System.Windows.Media.Color.FromRgb(45, 212, 191) : System.Windows.Media.Color.FromRgb(248, 113, 113));
    }

    private void RefreshStatus()
    {
        var isRunning = IsAppRunning();
        var envIssues = ValidateEnvironment();
        var stalePortIssue = IsPortInUse(ExtractPort(AppUrl)) && !isRunning;

        if (isRunning)
        {
            SetStatus("running", true, "Dashboard online and responding to requests.");
        }
        else if (envIssues.Count > 0)
        {
            SetStatus("environment issue", false, envIssues[0]);
        }
        else if (_startupInProgress)
        {
            SetStatus("starting", false, "Launching Next.js dashboard in the background.");
        }
        else
        {
            SetStatus("ready", true, "Environment is clean and launcher is waiting to start.");
        }

        _startBtn.IsEnabled = !isRunning && !_startupInProgress && envIssues.Count == 0;
        _startBtn.Background = new SolidColorBrush(!isRunning && !_startupInProgress && envIssues.Count == 0 ? System.Windows.Media.Color.FromRgb(14, 116, 144) : System.Windows.Media.Color.FromRgb(30, 41, 59));

        _stopBtn.IsEnabled = isRunning;
        _stopBtn.Background = new SolidColorBrush(isRunning ? System.Windows.Media.Color.FromRgb(51, 65, 85) : System.Windows.Media.Color.FromRgb(30, 41, 59));

        _killStaleBtn.IsEnabled = stalePortIssue;
        _killStaleBtn.Background = new SolidColorBrush(stalePortIssue ? System.Windows.Media.Color.FromRgb(120, 53, 15) : System.Windows.Media.Color.FromRgb(30, 41, 59));

        var browserOpened = File.Exists(_browserFlag);
        _openBtn.IsEnabled = isRunning && !browserOpened;
        _openBtn.Background = new SolidColorBrush(isRunning && !browserOpened ? System.Windows.Media.Color.FromRgb(14, 116, 144) : System.Windows.Media.Color.FromRgb(24, 24, 27));
    }

    private void MinimizeToTray()
    {
        _isWindowVisible = false;
        _window.Hide();
        _trayIcon?.Visible = true;
    }

    private void RestoreWindow()
    {
        _isWindowVisible = true;
        _window.Show();
        _window.WindowState = WindowState.Normal;
        _window.Activate();
    }

    private void StopApp(bool updateStatus = true)
    {
        try
        {
            if (File.Exists(_pidFile))
            {
                var value = File.ReadAllText(_pidFile).Trim();
                if (int.TryParse(value, out var pid))
                {
                    try
                    {
                        using var proc = Process.GetProcessById(pid);
                        proc.Kill(true);
                    }
                    catch { }
                }
                File.Delete(_pidFile);
            }

            foreach (var proc in Process.GetProcesses().Where(p => p.ProcessName.Contains("node", StringComparison.OrdinalIgnoreCase) || p.ProcessName.Contains("powershell", StringComparison.OrdinalIgnoreCase) || p.ProcessName.Contains("cmd", StringComparison.OrdinalIgnoreCase)).ToList())
            {
                var cmd = proc.StartInfo?.Arguments ?? string.Empty;
                var targetUrl = AppUrl;
                var host = ExtractHost(targetUrl);
                var port = ExtractPort(targetUrl);

                if (IsLikelyDevServer(cmd)
                    || cmd.Contains($"--hostname {host}", StringComparison.OrdinalIgnoreCase)
                    || cmd.Contains($"--port {port}", StringComparison.OrdinalIgnoreCase)
                    || cmd.Contains("sanctum-dashboard", StringComparison.OrdinalIgnoreCase))
                {
                    try { proc.Kill(true); } catch { }
                }
            }

            try { File.Delete(_browserFlag); } catch { }
        }
        catch { }

        if (updateStatus)
        {
            SetStatus("stopped", false, "Dashboard is stopped and waiting to be started.");
            AppendLog("[launcher] Stop command issued.");
        }

        RefreshStatus();
    }
}


using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Effects;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using WinForms = System.Windows.Forms;
using Wpf = System.Windows;

namespace SanctumSuiteLauncher;

public partial class App : Wpf.Application
{
    private readonly string _root = ResolveRepoRoot();
    private readonly string _appDir = Path.Combine(ResolveRepoRoot(), "sanctum-dashboard");
    private readonly string _pidFile = Path.Combine(ResolveRepoRoot(), ".sanctum-suite.pid");
    private readonly string _browserFlag = Path.Combine(ResolveRepoRoot(), ".sanctum-suite.browser-opened");
    private readonly HttpClient _client = new();
    private const string AppUrl = "http://localhost:3000";
    private Wpf.Window _window = null!;
    private readonly DispatcherTimer _timer = new();
    private Process? _nodeProcess;
    private Wpf.Controls.Button _startBtn = null!;
    private Wpf.Controls.Button _stopBtn = null!;
    private Wpf.Controls.Button _openBtn = null!;
    private Wpf.Controls.TextBlock _status = null!;
    private WinForms.NotifyIcon? _trayIcon;
    private bool _isWindowVisible = true;

    private static string ResolveRepoRoot()
    {
        var baseDir = AppDomain.CurrentDomain.BaseDirectory;
        var candidates = new[]
        {
            baseDir,
            Path.GetFullPath(Path.Combine(baseDir, "..", "..", "..", "..")),
            Path.GetFullPath(Path.Combine(baseDir, "..", "..", "..")),
            Path.GetFullPath(Path.Combine(baseDir, "..", "..")),
            Directory.GetCurrentDirectory()
        };

        foreach (var candidate in candidates)
        {
            if (Directory.Exists(candidate) && File.Exists(Path.Combine(candidate, "sanctum-dashboard", "package.json")))
            {
                return candidate;
            }
        }

        return baseDir;
    }

    protected override void OnStartup(StartupEventArgs e)
    {
        _window = new Window
        {
            Title = "Sanctum Suite",
            Width = 540,
            Height = 260,
            WindowStartupLocation = WindowStartupLocation.CenterScreen,
            ResizeMode = ResizeMode.NoResize,
            WindowStyle = WindowStyle.None,
            AllowsTransparency = true,
            Background = Wpf.Media.Brushes.Transparent,
            Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(226, 232, 240)),
            Icon = new BitmapImage(new Uri(Path.Combine(_root, "sanctum-suite-icon.ico"), UriKind.Absolute)),
            ShowInTaskbar = true,
            Topmost = false
        };

        _window.MouseLeftButtonDown += (_, _) => _window.DragMove();

        var shadow = new DropShadowEffect
        {
            Color = System.Windows.Media.Color.FromArgb(160, 15, 23, 42),
            BlurRadius = 28,
            ShadowDepth = 14,
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
            Padding = new Thickness(22),
            Margin = new Thickness(12),
            Effect = shadow
        };

        var content = new Grid();
        content.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        content.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        content.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

        var header = new Grid { Margin = new Thickness(0, 0, 0, 12) };
        header.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        header.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        header.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

        var title = new TextBlock
        {
            Text = "Sanctum Suite",
            FontSize = 28,
            FontWeight = FontWeights.Bold,
            Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(131, 224, 196)),
            VerticalAlignment = VerticalAlignment.Center
        };
        Grid.SetColumn(title, 0);

        var statusDot = new Border
        {
            Width = 10,
            Height = 10,
            CornerRadius = new CornerRadius(5),
            Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(100, 116, 139)),
            Margin = new Thickness(0, 0, 8, 0),
            VerticalAlignment = VerticalAlignment.Center
        };
        Grid.SetColumn(statusDot, 2);

        var closeBtn = new Wpf.Controls.Button
        {
            Content = "✕",
            Width = 28,
            Height = 28,
            Margin = new Thickness(10, 0, 0, 0),
            Background = new SolidColorBrush(System.Windows.Media.Color.FromArgb(80, 148, 163, 184)),
            Foreground = System.Windows.Media.Brushes.White,
            BorderThickness = new Thickness(0),
            Padding = new Thickness(0),
            ToolTip = "Zwin do zasobnika"
        };
        closeBtn.Click += (_, _) => MinimizeToTray();
        Grid.SetColumn(closeBtn, 2);

        header.Children.Add(title);
        header.Children.Add(statusDot);
        header.Children.Add(closeBtn);

        _status = new TextBlock
        {
            Text = "Status: stopped",
            FontSize = 15,
            Margin = new Thickness(0, 0, 0, 18),
            Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(226, 232, 240))
        };

        var infoBar = new Border
        {
            Background = new SolidColorBrush(System.Windows.Media.Color.FromArgb(35, 15, 118, 110)),
            Padding = new Thickness(14, 10, 14, 10),
            CornerRadius = new CornerRadius(12),
            Margin = new Thickness(0, 0, 0, 18)
        };
        var infoText = new TextBlock
        {
            Text = "Monitoring • Threats • Alerts • Investigations",
            Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(191, 219, 254)),
            FontSize = 12,
            FontWeight = FontWeights.SemiBold
        };
        infoBar.Child = infoText;

        var buttons = new StackPanel { Orientation = System.Windows.Controls.Orientation.Horizontal, Margin = new Thickness(0, 0, 0, 0) };

        _startBtn = new Wpf.Controls.Button
        {
            Content = "Start",
            Width = 150,
            Height = 44,
            Margin = new Thickness(0, 0, 12, 0),
            Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(14, 116, 144)),
            Foreground = System.Windows.Media.Brushes.White,
            BorderThickness = new Thickness(0),
            FontWeight = FontWeights.SemiBold,
            Cursor = System.Windows.Input.Cursors.Hand,
            Padding = new Thickness(0)
        };

        _stopBtn = new Wpf.Controls.Button
        {
            Content = "Stop",
            Width = 150,
            Height = 44,
            Margin = new Thickness(0, 0, 12, 0),
            Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(51, 65, 85)),
            Foreground = System.Windows.Media.Brushes.White,
            BorderThickness = new Thickness(0),
            FontWeight = FontWeights.SemiBold,
            Cursor = System.Windows.Input.Cursors.Hand,
            Padding = new Thickness(0)
        };

        _openBtn = new Wpf.Controls.Button
        {
            Content = "Open app",
            Width = 150,
            Height = 44,
            Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(24, 24, 27)),
            Foreground = System.Windows.Media.Brushes.White,
            BorderThickness = new Thickness(0),
            FontWeight = FontWeights.SemiBold,
            Cursor = System.Windows.Input.Cursors.Hand,
            Padding = new Thickness(0)
        };

        _startBtn.Click += async (_, _) => await StartAppAsync();
        _stopBtn.Click += (_, _) => StopApp();
        _openBtn.Click += (_, _) =>
        {
            if (!IsAppRunning()) return;
            TryOpenBrowser(false);
        };

        buttons.Children.Add(_startBtn);
        buttons.Children.Add(_stopBtn);
        buttons.Children.Add(_openBtn);

        Grid.SetRow(header, 0);
        Grid.SetRow(_status, 1);
        Grid.SetRow(infoBar, 2);
        Grid.SetRow(buttons, 3);

        content.Children.Add(header);
        content.Children.Add(_status);
        content.Children.Add(infoBar);
        content.Children.Add(buttons);

        outer.Child = content;
        _window.Content = outer;

        _trayIcon = new WinForms.NotifyIcon
        {
            Visible = true,
            Icon = new Icon(Path.Combine(_root, "sanctum-suite-icon.ico")),
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
        trayMenu.Items.Add(showItem);
        trayMenu.Items.Add(openItem);
        trayMenu.Items.Add(exitItem);
        _trayIcon.ContextMenuStrip = trayMenu;

        _timer.Interval = TimeSpan.FromSeconds(1);
        _timer.Tick += (_, _) => RefreshStatus();
        _timer.Start();

        _window.Show();
        _window.Activate();
        RefreshStatus();
        base.OnStartup(e);
    }

    private async Task StartAppAsync()
    {
        try
        {
            var appProjectDir = _appDir;

            if (IsAppRunning())
            {
                _status.Text = "Status: running";
                RefreshStatus();
                return;
            }

            if (!Directory.Exists(appProjectDir) || !File.Exists(Path.Combine(appProjectDir, "package.json")))
            {
                _status.Text = "Status: missing project";
                RefreshStatus();
                return;
            }

            if (!File.Exists(Path.Combine(appProjectDir, "node_modules", "next", "package.json")))
            {
                _status.Text = "Status: installing deps...";
                RefreshStatus();
                var install = Process.Start(new ProcessStartInfo("cmd.exe", $"/c cd /d \"{appProjectDir}\" && npm install --no-fund --no-audit") { UseShellExecute = true });
                if (install != null) install.WaitForExit();
            }

            StopApp(false);
            try { File.Delete(_browserFlag); } catch { }

            var startInfo = new ProcessStartInfo
            {
                FileName = "powershell.exe",
                Arguments = $"-NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command \"Set-Location '{appProjectDir}'; npm run dev -- --hostname 0.0.0.0 --port 3000\"",
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = false,
                RedirectStandardError = false,
            };

            _nodeProcess = Process.Start(startInfo);
            if (_nodeProcess != null)
            {
                File.WriteAllText(_pidFile, _nodeProcess.Id.ToString());
            }

            _status.Text = "Status: starting...";
            RefreshStatus();

            var started = false;
            for (var i = 0; i < 120; i++)
            {
                try
                {
                    var resp = await _client.GetAsync(AppUrl);
                    if (resp.IsSuccessStatusCode)
                    {
                        started = true;
                        break;
                    }
                }
                catch { }
                await Task.Delay(1000);
            }

            if (started)
            {
                _status.Text = "Status: running";
            }
            else
            {
                _status.Text = "Status: startup failed";
            }

            RefreshStatus();
        }
        catch (Exception ex)
        {
            _status.Text = "Status: error";
            RefreshStatus();
            Wpf.MessageBox.Show(ex.Message, "Sanctum Suite");
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

    private void OpenBrowserOnce()
    {
        TryOpenBrowser(true);
    }

    private bool IsAppRunning()
    {
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
                        return true;
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
                if ((processName.Contains("node", StringComparison.OrdinalIgnoreCase) || processName.Contains("powershell", StringComparison.OrdinalIgnoreCase))
                    && (cmd.Contains("next dev --hostname 0.0.0.0", StringComparison.OrdinalIgnoreCase)
                        || cmd.Contains("npm run dev", StringComparison.OrdinalIgnoreCase)
                        || cmd.Contains("port 3000", StringComparison.OrdinalIgnoreCase)))
                {
                    return true;
                }
            }
            catch { }
        }

        return false;
    }

    private void RefreshStatus()
    {
        var isRunning = IsAppRunning();
        _status.Text = isRunning ? "Status: running" : "Status: stopped";
        _status.Foreground = new SolidColorBrush(isRunning ? System.Windows.Media.Color.FromRgb(127, 247, 211) : System.Windows.Media.Color.FromRgb(226, 232, 240));
        _startBtn.IsEnabled = !isRunning;
        _startBtn.Background = new SolidColorBrush(isRunning ? System.Windows.Media.Color.FromRgb(30, 41, 59) : System.Windows.Media.Color.FromRgb(14, 116, 144));
        _stopBtn.IsEnabled = isRunning;
        _stopBtn.Background = new SolidColorBrush(isRunning ? System.Windows.Media.Color.FromRgb(51, 65, 85) : System.Windows.Media.Color.FromRgb(30, 41, 59));
        _openBtn.IsEnabled = isRunning && File.Exists(_browserFlag) == false;
        _openBtn.Background = new SolidColorBrush(isRunning && !File.Exists(_browserFlag) ? System.Windows.Media.Color.FromRgb(14, 116, 144) : System.Windows.Media.Color.FromRgb(24, 24, 27));

        if (_window != null)
        {
            var dot = (Border?)_window.FindName("statusDot");
            if (dot != null)
            {
                dot.Background = new SolidColorBrush(isRunning ? System.Windows.Media.Color.FromRgb(45, 212, 191) : System.Windows.Media.Color.FromRgb(100, 116, 139));
            }
        }
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
                if (cmd.Contains("next dev --hostname 0.0.0.0", StringComparison.OrdinalIgnoreCase)
                    || cmd.Contains("npm run dev", StringComparison.OrdinalIgnoreCase)
                    || cmd.Contains("port 3000", StringComparison.OrdinalIgnoreCase))
                {
                    try { proc.Kill(true); } catch { }
                }
            }

            try { File.Delete(_browserFlag); } catch { }
        }
        catch { }

        if (updateStatus)
        {
            _status.Text = "Status: stopped";
        }

        RefreshStatus();
    }
}

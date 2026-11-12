using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using WinForms = System.Windows.Forms;
using Wpf = System.Windows;

namespace SanctumSuiteLauncher;

public partial class App : Wpf.Application
{
    private readonly string _root = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", ".."));
    private readonly string _appDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "..");
    private readonly string _pidFile = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "..", ".sanctum-suite.pid");
    private readonly string _stdoutLog = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "..", "sanctum-suite-stdout.log");
    private readonly string _stderrLog = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "..", "sanctum-suite-stderr.log");
    private readonly string _browserFlag = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "..", ".sanctum-suite.browser-opened");
    private readonly HttpClient _client = new();
    private Wpf.Window _window = null!;
    private readonly DispatcherTimer _timer = new();
    private Process? _nodeProcess;
    private Wpf.Controls.Button _startBtn = null!;
    private Wpf.Controls.Button _stopBtn = null!;
    private Wpf.Controls.Button _openBtn = null!;
    private Wpf.Controls.TextBlock _status = null!;
    private WinForms.NotifyIcon? _trayIcon;
    private bool _isWindowVisible = true;

    protected override void OnStartup(StartupEventArgs e)
    {
        _window = new Window
        {
            Title = "Sanctum Suite",
            Width = 520,
            Height = 270,
            WindowStartupLocation = WindowStartupLocation.CenterScreen,
            ResizeMode = ResizeMode.NoResize,
            WindowStyle = WindowStyle.None,
            AllowsTransparency = true,
            Background = new SolidColorBrush(System.Windows.Media.Color.FromArgb(180, 10, 17, 25)),
            Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(226, 232, 240)),
            Icon = new BitmapImage(new Uri(Path.Combine(_root, "sanctum-suite-icon.ico"), UriKind.Absolute))
        };

        _window.MouseLeftButtonDown += (_, _) => _window.DragMove();

        var outer = new Border
        {
            CornerRadius = new CornerRadius(20),
            BorderBrush = new SolidColorBrush(System.Windows.Media.Color.FromArgb(120, 148, 163, 184)),
            BorderThickness = new Thickness(1),
            Background = new SolidColorBrush(System.Windows.Media.Color.FromArgb(180, 10, 17, 25)),
            Padding = new Thickness(20),
            Margin = new Thickness(8)
        };

        var stack = new StackPanel { Background = System.Windows.Media.Brushes.Transparent };
        var header = new Grid { Margin = new Thickness(0, 0, 0, 12) };
        header.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        header.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        header.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

        var title = new TextBlock { Text = "Sanctum Suite", FontSize = 30, FontWeight = FontWeights.Bold, Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(131, 224, 196)), Margin = new Thickness(0, 0, 0, 0) };
        Grid.SetColumn(title, 0);

        var icon = new Border
        {
            Width = 16,
            Height = 16,
            CornerRadius = new CornerRadius(8),
            Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(131, 224, 196)),
            Margin = new Thickness(0, 6, 0, 0),
            Child = new Border { Width = 8, Height = 8, CornerRadius = new CornerRadius(4), Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(10, 17, 25)) }
        };
        Grid.SetColumn(icon, 2);

        var closeBtn = new Wpf.Controls.Button
        {
            Content = "✕",
            Width = 26,
            Height = 26,
            Margin = new Thickness(8, 0, 0, 0),
            Background = new SolidColorBrush(System.Windows.Media.Color.FromArgb(120, 100, 116, 126)),
            Foreground = System.Windows.Media.Brushes.White,
            BorderThickness = new Thickness(0),
            Padding = new Thickness(0),
            ToolTip = "Close to tray"
        };
        closeBtn.Click += (_, _) => MinimizeToTray();
        Grid.SetColumn(closeBtn, 2);

        header.Children.Add(title);
        header.Children.Add(icon);
        header.Children.Add(closeBtn);

        _status = new TextBlock { Text = "Status: stopped", FontSize = 16, Margin = new Thickness(0, 0, 0, 18), Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(226, 232, 240)) };
        var buttons = new StackPanel { Orientation = System.Windows.Controls.Orientation.Horizontal, Margin = new Thickness(0, 0, 0, 12) };

        _startBtn = new Wpf.Controls.Button { Content = "Start", Width = 130, Height = 42, Margin = new Thickness(0, 0, 12, 0), Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(14, 116, 144)), Foreground = System.Windows.Media.Brushes.White, BorderThickness = new Thickness(0), FontWeight = FontWeights.SemiBold };
        _stopBtn = new Wpf.Controls.Button { Content = "Stop", Width = 130, Height = 42, Margin = new Thickness(0, 0, 12, 0), Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(51, 65, 85)), Foreground = System.Windows.Media.Brushes.White, BorderThickness = new Thickness(0), FontWeight = FontWeights.SemiBold };
        _openBtn = new Wpf.Controls.Button { Content = "Open app", Width = 130, Height = 42, Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(24, 24, 27)), Foreground = System.Windows.Media.Brushes.White, BorderThickness = new Thickness(0), FontWeight = FontWeights.SemiBold };

        _startBtn.Click += async (_, _) => await StartAppAsync();
        _stopBtn.Click += (_, _) => StopApp();
        _openBtn.Click += (_, _) =>
        {
            if (!IsAppRunning())
            {
                return;
            }

            Process.Start(new ProcessStartInfo("http://localhost:3000") { UseShellExecute = true });
            File.WriteAllText(_browserFlag, "opened");
        };

        buttons.Children.Add(_startBtn);
        buttons.Children.Add(_stopBtn);
        buttons.Children.Add(_openBtn);
        stack.Children.Add(header);
        stack.Children.Add(_status);
        stack.Children.Add(buttons);

        outer.Child = stack;
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
        var exitItem = new WinForms.ToolStripMenuItem("Exit");
        exitItem.Click += (_, _) =>
        {
            StopApp(false);
            _trayIcon.Visible = false;
            _window.Close();
        };
        trayMenu.Items.Add(showItem);
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
            if (IsAppRunning())
            {
                _status.Text = "Status: running";
                RefreshStatus();
                return;
            }

            if (!File.Exists(Path.Combine(_appDir, "sanctum-dashboard", "package.json")))
            {
                _status.Text = "Status: missing project";
                RefreshStatus();
                return;
            }

            if (!File.Exists(Path.Combine(_appDir, "sanctum-dashboard", "node_modules", "next", "package.json")))
            {
                _status.Text = "Status: installing deps...";
                RefreshStatus();
                var install = Process.Start(new ProcessStartInfo("cmd.exe", $"/c cd /d \"{Path.Combine(_appDir, "sanctum-dashboard")}\" && npm install --no-fund --no-audit") { UseShellExecute = true });
                install!.WaitForExit();
            }

            StopApp(false);
            File.Delete(_stdoutLog);
            File.Delete(_stderrLog);
            File.Delete(_browserFlag);

            _nodeProcess = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = "cmd.exe",
                    Arguments = $"/c cd /d \"{Path.Combine(_appDir, "sanctum-dashboard")}\" && npm run dev -- --hostname 0.0.0.0 > \"{_stdoutLog}\" 2> \"{_stderrLog}\"",
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = false,
                    RedirectStandardError = false,
                }
            };

            if (_nodeProcess.Start())
            {
                File.WriteAllText(_pidFile, _nodeProcess.Id.ToString());
            }

            _status.Text = "Status: starting...";
            RefreshStatus();
            var started = false;
            var browserOpened = false;

            for (var i = 0; i < 120; i++)
            {
                try
                {
                    var resp = await _client.GetAsync("http://localhost:3000");
                    if (resp.IsSuccessStatusCode)
                    {
                        started = true;
                        if (!browserOpened)
                        {
                            Process.Start(new ProcessStartInfo("http://localhost:3000") { UseShellExecute = true });
                            File.WriteAllText(_browserFlag, "opened");
                            browserOpened = true;
                        }
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

    private bool IsAppRunning()
    {
        if (File.Exists(_pidFile))
        {
            var value = File.ReadAllText(_pidFile).Trim();
            if (int.TryParse(value, out var pid))
            {
                try
                {
                    var proc = Process.GetProcessById(pid);
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
                if (cmd.Contains("next dev --hostname 0.0.0.0") || cmd.Contains("npm run dev"))
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
        _openBtn.IsEnabled = isRunning;
        _openBtn.Background = new SolidColorBrush(isRunning ? System.Windows.Media.Color.FromRgb(14, 116, 144) : System.Windows.Media.Color.FromRgb(24, 24, 27));
    }

    private void MinimizeToTray()
    {
        _isWindowVisible = false;
        _window.WindowState = WindowState.Minimized;
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
                    try { Process.GetProcessById(pid)?.Kill(true); } catch { }
                }
                File.Delete(_pidFile);
            }

            foreach (var proc in Process.GetProcesses().Where(p => p.ProcessName.Contains("node") || p.ProcessName.Contains("cmd")).ToList())
            {
                var cmd = proc.StartInfo?.Arguments ?? string.Empty;
                if (cmd.Contains("next dev --hostname 0.0.0.0") || cmd.Contains("npm run dev"))
                {
                    try { proc.Kill(true); } catch { }
                }
            }

            File.Delete(_browserFlag);
        }
        catch { }

        if (updateStatus)
        {
            _status.Text = "Status: stopped";
        }

        RefreshStatus();
    }
}

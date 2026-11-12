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

namespace SanctumSuiteLauncher;

public partial class App : Application
{
    private readonly string _root = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", ".."));
    private readonly string _appDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "..");
    private readonly string _pidFile = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "..", ".sanctum-suite.pid");
    private readonly string _stdoutLog = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "..", "sanctum-suite-stdout.log");
    private readonly string _stderrLog = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "..", "sanctum-suite-stderr.log");
    private readonly string _browserFlag = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "..", ".sanctum-suite.browser-opened");
    private readonly HttpClient _client = new();
    private Window _window;
    private readonly DispatcherTimer _timer = new();
    private Process? _nodeProcess;

    protected override void OnStartup(StartupEventArgs e)
    {
        _window = new Window
        {
            Title = "Sanctum Suite",
            Width = 420,
            Height = 220,
            WindowStartupLocation = WindowStartupLocation.CenterScreen,
            ResizeMode = ResizeMode.NoResize,
            Background = new SolidColorBrush(Color.FromRgb(10, 17, 25)),
            Foreground = new SolidColorBrush(Color.FromRgb(226, 232, 240)),
            Icon = new BitmapImage(new Uri(Path.Combine(_root, "sanctum-suite-icon.ico"), UriKind.Absolute))
        };

        var stack = new StackPanel { Margin = new Thickness(20), Background = new SolidColorBrush(Color.FromRgb(10, 17, 25)) };
        var title = new TextBlock { Text = "Sanctum Suite", FontSize = 28, FontWeight = FontWeights.Bold, Foreground = new SolidColorBrush(Color.FromRgb(131, 224, 196)), Margin = new Thickness(0, 0, 0, 12) };
        var status = new TextBlock { Text = "Status: stopped", FontSize = 16, Margin = new Thickness(0, 0, 0, 18), Foreground = new SolidColorBrush(Color.FromRgb(226, 232, 240)) };
        var buttons = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 0, 0, 10) };

        var startBtn = new Button { Content = "Start", Width = 110, Height = 36, Margin = new Thickness(0, 0, 12, 0), Background = new SolidColorBrush(Color.FromRgb(14, 116, 144)), Foreground = Brushes.White, BorderThickness = new Thickness(0) };
        var stopBtn = new Button { Content = "Stop", Width = 110, Height = 36, Margin = new Thickness(0, 0, 12, 0), Background = new SolidColorBrush(Color.FromRgb(51, 65, 85)), Foreground = Brushes.White, BorderThickness = new Thickness(0) };
        var openBtn = new Button { Content = "Open app", Width = 110, Height = 36, Background = new SolidColorBrush(Color.FromRgb(24, 24, 27)), Foreground = Brushes.White, BorderThickness = new Thickness(0) };

        startBtn.Click += async (_, _) => await StartAppAsync(status);
        stopBtn.Click += (_, _) => StopApp(status);
        openBtn.Click += (_, _) =>
        {
            Process.Start(new ProcessStartInfo("http://localhost:3000") { UseShellExecute = true });
            File.WriteAllText(_browserFlag, "opened");
        };

        buttons.Children.Add(startBtn);
        buttons.Children.Add(stopBtn);
        buttons.Children.Add(openBtn);
        stack.Children.Add(title);
        stack.Children.Add(status);
        stack.Children.Add(buttons);

        _window.Content = stack;
        _window.Show();
        base.OnStartup(e);
    }

    private async Task StartAppAsync(TextBlock status)
    {
        try
        {
            if (!File.Exists(Path.Combine(_appDir, "sanctum-dashboard", "package.json")))
            {
                status.Text = "Status: missing project";
                return;
            }

            if (!File.Exists(Path.Combine(_appDir, "sanctum-dashboard", "node_modules", "next", "package.json")))
            {
                status.Text = "Status: installing deps...";
                var install = Process.Start(new ProcessStartInfo("cmd.exe", $"/c cd /d \"{Path.Combine(_appDir, "sanctum-dashboard")}\" && npm install --no-fund --no-audit") { UseShellExecute = true });
                install!.WaitForExit();
            }

            StopApp(status, false);
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

            status.Text = "Status: starting...";
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
                status.Text = "Status: running";
            }
            else
            {
                status.Text = "Status: startup failed";
            }
        }
        catch (Exception ex)
        {
            status.Text = "Status: error";
            MessageBox.Show(ex.Message, "Sanctum Suite");
        }
    }

    private void StopApp(TextBlock status, bool updateStatus = true)
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
            status.Text = "Status: stopped";
        }
    }
}

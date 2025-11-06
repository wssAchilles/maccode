using TdLib;

namespace MyTelegramApp.Services;

public class TelegramService : ITelegramService
{
    private readonly TdClient _client;

    public event EventHandler<TdApi.Update>? OnUpdateReceived;

    public TelegramService()
    {
        // Use custom bindings for Mac Catalyst
        var bindings = new MacCatalystTdLibBindings();
        
        // Set up TDLib logging to file for detailed diagnostics
        var logPath = Path.Combine(FileSystem.AppDataDirectory, "tdlib-logs");
        Directory.CreateDirectory(logPath);
        var logFile = Path.Combine(logPath, "tdlib.log");
        
        // Set log verbosity level to VERBOSE (most detailed)
        bindings.SetLogVerbosityLevel(5); // 5 = VERBOSE
        System.Diagnostics.Debug.WriteLine($"TelegramService: Set TDLib log level to VERBOSE (5)");
        System.Diagnostics.Debug.WriteLine($"TelegramService: Log file path: {logFile}");
        
        // Set log file path
        try
        {
            var logFileBytes = System.Text.Encoding.UTF8.GetBytes(logFile);
            var logFilePtr = System.Runtime.InteropServices.Marshal.AllocHGlobal(logFileBytes.Length + 1);
            System.Runtime.InteropServices.Marshal.Copy(logFileBytes, 0, logFilePtr, logFileBytes.Length);
            System.Runtime.InteropServices.Marshal.WriteByte(logFilePtr, logFileBytes.Length, 0);
            bindings.SetLogFilePath(logFilePtr);
            System.Runtime.InteropServices.Marshal.FreeHGlobal(logFilePtr);
            System.Diagnostics.Debug.WriteLine($"TelegramService: Log file configured successfully");
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"TelegramService: Failed to set log file: {ex.Message}");
        }
        
        _client = new TdClient(bindings);
        _client.UpdateReceived += OnClientUpdateReceived;
        
        System.Diagnostics.Debug.WriteLine("TelegramService: TdClient created and update handler registered");
    }

    private void OnClientUpdateReceived(object? sender, TdApi.Update update)
    {
        var timestamp = DateTime.Now.ToString("HH:mm:ss.fff");
        var updateType = update.GetType().Name;
        
        // Log all updates for debugging
        System.Diagnostics.Debug.WriteLine($"[{timestamp}] TelegramService: 📨 Update received: {updateType}");
        
        // Special logging for important update types
        switch (update)
        {
            case TdApi.Update.UpdateAuthorizationState authState:
                var stateName = authState.AuthorizationState.GetType().Name;
                System.Diagnostics.Debug.WriteLine($"[{timestamp}] TelegramService: 🔐 Authorization state changed to: {stateName}");
                break;
                
            case TdApi.Update.UpdateConnectionState connState:
                var connectionType = connState.State.GetType().Name;
                System.Diagnostics.Debug.WriteLine($"[{timestamp}] TelegramService: 🌐 Connection state changed to: {connectionType}");
                break;
                
            case TdApi.Update.UpdateOption option:
                System.Diagnostics.Debug.WriteLine($"[{timestamp}] TelegramService: ⚙️  Option update: {option.Name} = {option.Value}");
                break;
        }
        
        OnUpdateReceived?.Invoke(this, update);
    }

    public Task InitializeAsync()
    {
        // TdClient starts processing updates automatically when created
        return Task.CompletedTask;
    }

    public async Task<TdApi.Ok> ExecuteAuthenticationCommand(TdApi.Function<TdApi.Ok> command)
    {
        var commandName = command.GetType().Name;
        System.Diagnostics.Debug.WriteLine($"TelegramService: 📤 Executing authentication command: {commandName}");
        
        try
        {
            // All authentication commands should use Send() method
            // because they trigger state changes that are returned via UpdateAuthorizationState
            System.Diagnostics.Debug.WriteLine($"TelegramService: Using Send() for {commandName}");
            _client.Send(command);
            System.Diagnostics.Debug.WriteLine($"TelegramService: ✅ {commandName} sent successfully");
            System.Diagnostics.Debug.WriteLine($"TelegramService: ⏳ Waiting for UpdateAuthorizationState...");
            
            // Return immediately - the result will come via UpdateAuthorizationState
            return new TdApi.Ok();
        }
        catch (TdException tdEx)
        {
            System.Diagnostics.Debug.WriteLine($"TelegramService: ❌ TDLib error in {commandName}");
            System.Diagnostics.Debug.WriteLine($"TelegramService: Error code: {tdEx.Error.Code}");
            System.Diagnostics.Debug.WriteLine($"TelegramService: Error message: {tdEx.Error.Message}");
            throw;
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"TelegramService: ❌ Unexpected error in {commandName}: {ex.Message}");
            System.Diagnostics.Debug.WriteLine($"TelegramService: Stack trace: {ex.StackTrace}");
            throw;
        }
    }

    public async Task<T> ExecuteAsync<T>(TdApi.Function<T> command) where T : TdApi.Object
    {
        return await _client.ExecuteAsync(command);
    }
}

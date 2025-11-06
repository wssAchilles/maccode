using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using MyTelegramApp.Services;
using MyTelegramApp.Views;
using TdLib;

namespace MyTelegramApp.ViewModels;

public partial class LoginViewModel : ObservableObject
{
    private readonly ITelegramService _telegramService;

    // State properties
    [ObservableProperty]
    private string phoneNumber = string.Empty;

    [ObservableProperty]
    private string verificationCode = string.Empty;

    [ObservableProperty]
    private string twoFactorPassword = string.Empty;

    [ObservableProperty]
    private bool isWaitingForPhoneNumber = false;

    [ObservableProperty]
    private bool isWaitingForCode = false;

    [ObservableProperty]
    private bool isWaitingForPassword = false;

    [ObservableProperty]
    private bool isSubmitting = false;

    public LoginViewModel(ITelegramService telegramService)
    {
        _telegramService = telegramService;
        
        System.Diagnostics.Debug.WriteLine("LoginViewModel: Constructor called");
        
        // Subscribe to TDLib updates
        _telegramService.OnUpdateReceived += OnUpdateReceived;
        System.Diagnostics.Debug.WriteLine("LoginViewModel: Subscribed to updates");
        
        // Start TDLib initialization (don't await - let it run in background)
        _ = _telegramService.InitializeAsync();
        System.Diagnostics.Debug.WriteLine("LoginViewModel: InitializeAsync called");
    }

    private void OnUpdateReceived(object? sender, TdApi.Update update)
    {
        var updateType = update.GetType().Name;
        var timestamp = DateTime.Now.ToString("HH:mm:ss.fff");
        System.Diagnostics.Debug.WriteLine($"[{timestamp}] LoginViewModel: 📩 Received update: {updateType}");
        
        // Check if this is an authorization state update
        if (update is TdApi.Update.UpdateAuthorizationState authState)
        {
            var stateName = authState.AuthorizationState.GetType().Name;
            System.Diagnostics.Debug.WriteLine($"[{timestamp}] LoginViewModel: 🔐 Auth state update: {stateName}");
            
            // Handle on main thread
            MainThread.BeginInvokeOnMainThread(async () =>
            {
                System.Diagnostics.Debug.WriteLine($"[{timestamp}] LoginViewModel: 🎯 Dispatched to main thread");
                await HandleAuthorizationUpdate(authState);
            });
        }
        else if (update is TdApi.Update.UpdateConnectionState connState)
        {
            var connectionType = connState.State.GetType().Name;
            System.Diagnostics.Debug.WriteLine($"[{timestamp}] LoginViewModel: 🌐 Connection state: {connectionType}");
            
            // Log detailed connection state information
            switch (connState.State)
            {
                case TdApi.ConnectionState.ConnectionStateWaitingForNetwork:
                    System.Diagnostics.Debug.WriteLine($"[{timestamp}] LoginViewModel: ⚠️  Waiting for network connection");
                    break;
                case TdApi.ConnectionState.ConnectionStateConnecting:
                    System.Diagnostics.Debug.WriteLine($"[{timestamp}] LoginViewModel: 🔄 Connecting to Telegram servers...");
                    break;
                case TdApi.ConnectionState.ConnectionStateConnectingToProxy:
                    System.Diagnostics.Debug.WriteLine($"[{timestamp}] LoginViewModel: 🔄 Connecting via proxy...");
                    break;
                case TdApi.ConnectionState.ConnectionStateUpdating:
                    System.Diagnostics.Debug.WriteLine($"[{timestamp}] LoginViewModel: ⬇️  Downloading updates from server...");
                    break;
                case TdApi.ConnectionState.ConnectionStateReady:
                    System.Diagnostics.Debug.WriteLine($"[{timestamp}] LoginViewModel: ✅ Connected to Telegram servers!");
                    break;
            }
        }
        else if (update is TdApi.Update.UpdateOption option)
        {
            System.Diagnostics.Debug.WriteLine($"[{timestamp}] LoginViewModel: ⚙️  Option: {option.Name} = {option.Value}");
        }
        else
        {
            // Log other update types for debugging
            System.Diagnostics.Debug.WriteLine($"[{timestamp}] LoginViewModel: ℹ️  Other update: {updateType}");
        }
    }

    private async Task HandleAuthorizationUpdate(TdApi.Update.UpdateAuthorizationState authState)
    {
        System.Diagnostics.Debug.WriteLine($"LoginViewModel: HandleAuthorizationUpdate called with state: {authState.AuthorizationState.GetType().Name}");
        
        switch (authState.AuthorizationState)
        {
            case TdApi.AuthorizationState.AuthorizationStateWaitTdlibParameters:
                System.Diagnostics.Debug.WriteLine("LoginViewModel: Sending TDLib parameters...");
                try
                {
                    var dbDirectory = Path.Combine(FileSystem.AppDataDirectory, "tdlib-data");
                    var filesDirectory = Path.Combine(FileSystem.AppDataDirectory, "tdlib-files");
                    
                    System.Diagnostics.Debug.WriteLine($"LoginViewModel: Preparing TDLib parameters...");
                    System.Diagnostics.Debug.WriteLine($"LoginViewModel: Database directory: {dbDirectory}");
                    System.Diagnostics.Debug.WriteLine($"LoginViewModel: Files directory: {filesDirectory}");
                    
                    // Ensure directories exist
                    Directory.CreateDirectory(dbDirectory);
                    Directory.CreateDirectory(filesDirectory);
                    
                    // Create TDLib parameters with all required fields
                    // Based on official TDLib documentation and examples
                    // IMPORTANT: All string fields MUST be non-null
                    var parameters = new TdApi.SetTdlibParameters
                    {
                        // API credentials
                        ApiId = 20071395,
                        ApiHash = "14d6fe18fe46a543db98a82fde0f7197",
                        
                        // Test DC setting
                        UseTestDc = false,
                        
                        // Database settings
                        DatabaseDirectory = dbDirectory,
                        FilesDirectory = filesDirectory,
                        DatabaseEncryptionKey = new byte[0], // Empty array for no encryption
                        UseFileDatabase = true,
                        UseChatInfoDatabase = true,
                        UseMessageDatabase = true,
                        UseSecretChats = false,
                        
                        // Device information - must be non-empty strings
                        SystemLanguageCode = "en",
                        DeviceModel = "MacBook Pro",
                        SystemVersion = "macOS 14",
                        ApplicationVersion = "1.0.0"
                    };
                    
                    // Validate that no required string fields are null or empty
                    if (string.IsNullOrEmpty(parameters.DatabaseDirectory))
                        throw new InvalidOperationException("DatabaseDirectory cannot be null or empty");
                    if (string.IsNullOrEmpty(parameters.FilesDirectory))
                        throw new InvalidOperationException("FilesDirectory cannot be null or empty");
                    if (string.IsNullOrEmpty(parameters.ApiHash))
                        throw new InvalidOperationException("ApiHash cannot be null or empty");
                    if (string.IsNullOrEmpty(parameters.SystemLanguageCode))
                        throw new InvalidOperationException("SystemLanguageCode cannot be null or empty");
                    if (string.IsNullOrEmpty(parameters.DeviceModel))
                        throw new InvalidOperationException("DeviceModel cannot be null or empty");
                    if (string.IsNullOrEmpty(parameters.SystemVersion))
                        throw new InvalidOperationException("SystemVersion cannot be null or empty");
                    if (string.IsNullOrEmpty(parameters.ApplicationVersion))
                        throw new InvalidOperationException("ApplicationVersion cannot be null or empty");
                    
                    // Detailed validation logging
                    System.Diagnostics.Debug.WriteLine($"=== TDLib Parameters Debug ===");
                    System.Diagnostics.Debug.WriteLine($"ApiId: {parameters.ApiId}");
                    System.Diagnostics.Debug.WriteLine($"ApiHash: {(string.IsNullOrEmpty(parameters.ApiHash) ? "NULL/EMPTY" : "SET")}");
                    System.Diagnostics.Debug.WriteLine($"UseTestDc: {parameters.UseTestDc}");
                    System.Diagnostics.Debug.WriteLine($"DatabaseDirectory: {(string.IsNullOrEmpty(parameters.DatabaseDirectory) ? "NULL/EMPTY" : parameters.DatabaseDirectory)}");
                    System.Diagnostics.Debug.WriteLine($"FilesDirectory: {(string.IsNullOrEmpty(parameters.FilesDirectory) ? "NULL/EMPTY" : parameters.FilesDirectory)}");
                    System.Diagnostics.Debug.WriteLine($"DatabaseEncryptionKey: {(parameters.DatabaseEncryptionKey == null ? "NULL" : $"Length={parameters.DatabaseEncryptionKey.Length}")}");
                    System.Diagnostics.Debug.WriteLine($"UseFileDatabase: {parameters.UseFileDatabase}");
                    System.Diagnostics.Debug.WriteLine($"UseChatInfoDatabase: {parameters.UseChatInfoDatabase}");
                    System.Diagnostics.Debug.WriteLine($"UseMessageDatabase: {parameters.UseMessageDatabase}");
                    System.Diagnostics.Debug.WriteLine($"UseSecretChats: {parameters.UseSecretChats}");
                    System.Diagnostics.Debug.WriteLine($"SystemLanguageCode: {(string.IsNullOrEmpty(parameters.SystemLanguageCode) ? "NULL/EMPTY" : parameters.SystemLanguageCode)}");
                    System.Diagnostics.Debug.WriteLine($"DeviceModel: {(string.IsNullOrEmpty(parameters.DeviceModel) ? "NULL/EMPTY" : parameters.DeviceModel)}");
                    System.Diagnostics.Debug.WriteLine($"SystemVersion: {(string.IsNullOrEmpty(parameters.SystemVersion) ? "NULL/EMPTY" : parameters.SystemVersion)}");
                    System.Diagnostics.Debug.WriteLine($"ApplicationVersion: {(string.IsNullOrEmpty(parameters.ApplicationVersion) ? "NULL/EMPTY" : parameters.ApplicationVersion)}");
                    System.Diagnostics.Debug.WriteLine($"================================");
                    
                    System.Diagnostics.Debug.WriteLine("LoginViewModel: Executing SetTdlibParameters...");
                    await _telegramService.ExecuteAuthenticationCommand(parameters);
                    System.Diagnostics.Debug.WriteLine("LoginViewModel: ✅ Command sent successfully!");
                    System.Diagnostics.Debug.WriteLine("LoginViewModel: ⏳ Waiting for next state update (should be WaitPhoneNumber)...");
                    
                    // Start a timeout timer to detect if we're stuck
                    _ = Task.Run(async () =>
                    {
                        await Task.Delay(5000); // 5 seconds timeout
                        System.Diagnostics.Debug.WriteLine("LoginViewModel: ⚠️  WARNING: 5 seconds passed without receiving WaitPhoneNumber state!");
                        System.Diagnostics.Debug.WriteLine("LoginViewModel: This might indicate:");
                        System.Diagnostics.Debug.WriteLine("LoginViewModel:   1. Invalid API credentials");
                        System.Diagnostics.Debug.WriteLine("LoginViewModel:   2. Network connectivity issues");
                        System.Diagnostics.Debug.WriteLine("LoginViewModel:   3. TDLib stuck in processing");
                    });
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"LoginViewModel: ❌ ERROR: {ex.Message}");
                    System.Diagnostics.Debug.WriteLine($"LoginViewModel: Stack trace: {ex.StackTrace}");
                    
                    // Try to get inner exception details
                    if (ex.InnerException != null)
                    {
                        System.Diagnostics.Debug.WriteLine($"LoginViewModel: Inner exception: {ex.InnerException.Message}");
                    }
                }
                break;

            case TdApi.AuthorizationState.AuthorizationStateWaitPhoneNumber:
                System.Diagnostics.Debug.WriteLine("LoginViewModel: Setting IsWaitingForPhoneNumber = true");
                // TDLib is requesting phone number
                IsWaitingForPhoneNumber = true;
                IsWaitingForCode = false;
                IsWaitingForPassword = false;
                System.Diagnostics.Debug.WriteLine($"LoginViewModel: IsWaitingForPhoneNumber = {IsWaitingForPhoneNumber}");
                break;

            case TdApi.AuthorizationState.AuthorizationStateWaitCode:
                // TDLib is requesting verification code
                IsWaitingForPhoneNumber = false;
                IsWaitingForCode = true;
                IsWaitingForPassword = false;
                break;

            case TdApi.AuthorizationState.AuthorizationStateWaitPassword:
                // TDLib is requesting 2FA password
                IsWaitingForPhoneNumber = false;
                IsWaitingForCode = false;
                IsWaitingForPassword = true;
                break;

            case TdApi.AuthorizationState.AuthorizationStateReady:
                // Login successful! Navigate to chat list
                await Shell.Current.GoToAsync($"//{nameof(ChatListPage)}");
                break;

            default:
                // Log unhandled states
                System.Diagnostics.Debug.WriteLine($"Unhandled authorization state: {authState.AuthorizationState.GetType().Name}");
                break;
        }
    }

    [RelayCommand]
    private async Task Submit()
    {
        IsSubmitting = true;

        try
        {
            if (IsWaitingForPhoneNumber)
            {
                // Submit phone number
                await _telegramService.ExecuteAuthenticationCommand(
                    new TdApi.SetAuthenticationPhoneNumber
                    {
                        PhoneNumber = PhoneNumber
                    });
            }
            else if (IsWaitingForCode)
            {
                // Submit verification code
                await _telegramService.ExecuteAuthenticationCommand(
                    new TdApi.CheckAuthenticationCode
                    {
                        Code = VerificationCode
                    });
            }
            else if (IsWaitingForPassword)
            {
                // Submit 2FA password
                await _telegramService.ExecuteAuthenticationCommand(
                    new TdApi.CheckAuthenticationPassword
                    {
                        Password = TwoFactorPassword
                    });
            }
        }
        catch (TdException ex)
        {
            // Display error to user
            await Shell.Current.DisplayAlert("登录错误", ex.Message, "确定");
        }
        finally
        {
            IsSubmitting = false;
        }
    }
}

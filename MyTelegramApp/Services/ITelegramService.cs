using TdLib;

namespace MyTelegramApp.Services;

public interface ITelegramService
{
    event EventHandler<TdApi.Update>? OnUpdateReceived;
    
    Task InitializeAsync();
    
    Task<TdApi.Ok> ExecuteAuthenticationCommand(TdApi.Function<TdApi.Ok> command);
    
    Task<T> ExecuteAsync<T>(TdApi.Function<T> command) where T : TdApi.Object;
}

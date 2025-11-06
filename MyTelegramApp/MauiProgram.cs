using Microsoft.Extensions.Logging;
using MyTelegramApp.Services;
using MyTelegramApp.ViewModels;
using MyTelegramApp.Views;

namespace MyTelegramApp;

public static class MauiProgram
{
	public static MauiApp CreateMauiApp()
	{
		var builder = MauiApp.CreateBuilder();
		builder
			.UseMauiApp<App>()
			.ConfigureFonts(fonts =>
			{
				fonts.AddFont("OpenSans-Regular.ttf", "OpenSansRegular");
				fonts.AddFont("OpenSans-Semibold.ttf", "OpenSansSemibold");
			});

#if DEBUG
		builder.Logging.AddDebug();
#endif

		// Register Services
		builder.Services.AddSingleton<ITelegramService, TelegramService>();

		// Register ViewModels
		builder.Services.AddTransient<LoginViewModel>();
		builder.Services.AddTransient<ChatListViewModel>();
		builder.Services.AddTransient<ChatPageViewModel>();

		// Register Views
		builder.Services.AddTransient<LoginPage>();
		builder.Services.AddTransient<ChatListPage>();
		builder.Services.AddTransient<ChatPage>();

		return builder.Build();
	}
}

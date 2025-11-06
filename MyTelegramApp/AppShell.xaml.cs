using MyTelegramApp.Views;

namespace MyTelegramApp;

public partial class AppShell : Shell
{
	public AppShell()
	{
		InitializeComponent();

		// Register routes for navigation
		Routing.RegisterRoute(nameof(ChatListPage), typeof(ChatListPage));
		Routing.RegisterRoute(nameof(ChatPage), typeof(ChatPage));
	}
}

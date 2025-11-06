using MyTelegramApp.ViewModels;

namespace MyTelegramApp.Views;

public partial class ChatListPage : ContentPage
{
    public ChatListPage(ChatListViewModel viewModel)
    {
        InitializeComponent();
        BindingContext = viewModel;
    }
}

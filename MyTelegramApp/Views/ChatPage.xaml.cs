using MyTelegramApp.ViewModels;

namespace MyTelegramApp.Views;

public partial class ChatPage : ContentPage
{
    public ChatPage(ChatPageViewModel viewModel)
    {
        InitializeComponent();
        BindingContext = viewModel;
    }
}

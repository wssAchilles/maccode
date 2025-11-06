using System.Runtime.InteropServices;
using System.Text;
using TdLib.Bindings;

namespace MyTelegramApp.Services;

/// <summary>
/// Custom TdLib bindings for Mac Catalyst
/// </summary>
public class MacCatalystTdLibBindings : ITdLibBindings
{
    private const string LibraryName = "libtdjson";

    [DllImport(LibraryName, CallingConvention = CallingConvention.Cdecl)]
    private static extern IntPtr td_json_client_create();

    [DllImport(LibraryName, CallingConvention = CallingConvention.Cdecl)]
    private static extern void td_json_client_destroy(IntPtr client);

    [DllImport(LibraryName, CallingConvention = CallingConvention.Cdecl)]
    private static extern void td_json_client_send(IntPtr client, IntPtr request);

    [DllImport(LibraryName, CallingConvention = CallingConvention.Cdecl)]
    private static extern IntPtr td_json_client_receive(IntPtr client, double timeout);

    [DllImport(LibraryName, CallingConvention = CallingConvention.Cdecl)]
    private static extern IntPtr td_json_client_execute(IntPtr client, IntPtr request);

    [DllImport(LibraryName, CallingConvention = CallingConvention.Cdecl)]
    private static extern void td_set_log_verbosity_level(int level);

    [DllImport(LibraryName, CallingConvention = CallingConvention.Cdecl)]
    private static extern void td_set_log_file_path(IntPtr path);

    [DllImport(LibraryName, CallingConvention = CallingConvention.Cdecl)]
    private static extern void td_set_log_max_file_size(long size);

    public nint ClientCreate()
    {
        return td_json_client_create();
    }

    public void ClientDestroy(nint client)
    {
        td_json_client_destroy(client);
    }

    public void ClientSend(nint client, nint request)
    {
        td_json_client_send(client, request);
    }

    public nint ClientReceive(nint client, double timeout)
    {
        return td_json_client_receive(client, timeout);
    }

    public nint ClientExecute(nint client, nint request)
    {
        return td_json_client_execute(client, request);
    }

    public void SetLogVerbosityLevel(int level)
    {
        td_set_log_verbosity_level(level);
    }

    public int SetLogFilePath(nint path)
    {
        td_set_log_file_path(path);
        return 1;
    }

    public void SetLogFileMaxSize(long size)
    {
        td_set_log_max_file_size(size);
    }

    public void SetLogFatalErrorCallback(Callback? callback)
    {
        // Not implemented for Mac Catalyst
    }
}


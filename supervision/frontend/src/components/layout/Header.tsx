interface HeaderProps {
  status: "demo" | "live" | "error";
}

export function Header({ status }: HeaderProps) {
  const label = status === "live" ? "后端在线" : "Demo 数据";
  return (
    <header className="topbar">
      <div>
        <h1>交通感知实验大屏</h1>
        <p>本地 CV 统计 JSON 与云端 LLM 路况解析链路</p>
      </div>
      <span className={status === "live" ? "status live" : "status"}>{label}</span>
    </header>
  );
}

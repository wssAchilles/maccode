export function DataGridMotion() {
  return (
    <div className="motion-grid" aria-hidden="true">
      {Array.from({ length: 96 }, (_, index) => (
        <span key={index} />
      ))}
    </div>
  );
}

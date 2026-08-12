export function ErrorState({ message }: { message: string }) {
  return (
    <div className="state-block">
      Не удалось загрузить данные.
      <br />
      {message}
    </div>
  );
}

interface ItemCountProps {
  shown: number;
  total: number;
}

export function ItemCount({ shown, total }: ItemCountProps) {
  const noun = total === 1 ? "item" : "items";
  return (
    <p className="item-count">
      {shown === total ? `${total} ${noun}` : `${shown} of ${total} ${noun}`}
    </p>
  );
}

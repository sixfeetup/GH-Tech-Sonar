import { Link, type LinkProps } from "react-router-dom";

import { useMediaQuery } from "../useMediaQuery";

interface ItemLinkProps extends Omit<LinkProps, "rel" | "target" | "to"> {
  number: number;
}

export function ItemLink({ number, ...props }: ItemLinkProps) {
  const isMobile = useMediaQuery("(max-width: 767px)");

  return (
    <Link
      {...props}
      rel={isMobile ? undefined : "noopener noreferrer"}
      target={isMobile ? undefined : "_blank"}
      to={`/items/${number}`}
    />
  );
}

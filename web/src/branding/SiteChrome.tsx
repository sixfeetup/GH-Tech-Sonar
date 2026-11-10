import type { ReactNode } from "react";
import { Link } from "react-router-dom";

const SIX_FEET_UP_URL = "https://www.sixfeetup.com";

export function SiteHeader({ actions }: { actions?: ReactNode }) {
  return (
    <header className="site-header">
      <div className="site-header-inner">
        <a
          className="brand-logo-link"
          href={SIX_FEET_UP_URL}
          rel="noreferrer"
          target="_blank"
        >
          <img
            alt="Six Feet Up"
            className="brand-logo"
            height="48"
            src="/sfu-logo-trimmed.webp"
            width="141"
          />
        </a>
        <Link className="site-title" to="/">
          Tech Sonar
        </Link>
        {actions && <div className="site-header-actions">{actions}</div>}
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <p>© Six Feet Up. Solving hard software problems since 1999.</p>
        <a
          className="cta"
          href={`${SIX_FEET_UP_URL}/contact-us`}
          rel="noreferrer"
          target="_blank"
        >
          Let&apos;s Talk
        </a>
      </div>
    </footer>
  );
}

export function SiteLayout({
  actions,
  children,
}: {
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <>
      <SiteHeader actions={actions} />
      <main>{children}</main>
      <SiteFooter />
    </>
  );
}

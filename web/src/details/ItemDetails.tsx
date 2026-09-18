import DOMPurify from "dompurify";
import { Link, useNavigate, useParams } from "react-router-dom";

import type { SonarSnapshot } from "../data/sonar";
import { useMediaQuery } from "../useMediaQuery";

interface ItemDetailsProps {
  snapshot: SonarSnapshot;
}

const updatedAtFormatter = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "long",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  timeZone: "UTC",
  timeZoneName: "short",
});

export function ItemDetails({ snapshot }: ItemDetailsProps) {
  const { number } = useParams();
  const navigate = useNavigate();
  const isMobile = useMediaQuery("(max-width: 767px)");
  const item = snapshot.items.find(
    (candidate) => candidate.number === Number(number),
  );

  if (!item) {
    return (
      <section className="item-details">
        <h1>Sonar item not found</h1>
        <Link to="/">Back to Tech Sonar</Link>
      </section>
    );
  }

  const sanitizedBodyHtml = DOMPurify.sanitize(item.bodyHtml);

  return (
    <article className="item-details">
      <nav aria-label="Item navigation" className="item-navigation">
        {isMobile && (
          <button type="button" onClick={() => navigate(-1)}>
            Back
          </button>
        )}
        <Link to="/">Back to Tech Sonar</Link>
      </nav>

      <h1>{item.title}</h1>
      <dl className="item-metadata">
        <div>
          <dt>State</dt>
          <dd>{item.state}</dd>
        </div>
        <div>
          <dt>Statuses</dt>
          <dd>{item.statuses.join(", ")}</dd>
        </div>
        <div>
          <dt>Categories</dt>
          <dd>{item.categories.join(", ")}</dd>
        </div>
        <div>
          <dt>Updated</dt>
          <dd>
            <time dateTime={item.updatedAt}>
              {updatedAtFormatter.format(new Date(item.updatedAt))}
            </time>
          </dd>
        </div>
      </dl>

      {item.warnings.length > 0 && (
        <section aria-labelledby="item-warnings-heading">
          <h2 id="item-warnings-heading">Warnings</h2>
          <ul className="warnings">
            {item.warnings.map((warning) => (
              <li key={`${warning.code}-${warning.status}`}>
                <span aria-hidden="true">⚠ </span>
                {warning.message}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="item-body-heading">
        <h2 id="item-body-heading">Issue details</h2>
        <div
          className="item-body"
          dangerouslySetInnerHTML={{ __html: sanitizedBodyHtml }}
        />
      </section>

      {item.pullRequests.length > 0 && (
        <section aria-labelledby="item-pull-requests-heading">
          <h2 id="item-pull-requests-heading">Supporting pull requests</h2>
          <ul className="pull-requests">
            {item.pullRequests.map((pullRequest) => (
              <li key={pullRequest.number}>
                <a href={pullRequest.url}>
                  PR #{pullRequest.number}: {pullRequest.title} (
                  {pullRequest.state})
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}

      <p>
        <a href={item.url}>View issue and history on GitHub</a>
      </p>
    </article>
  );
}

import type { SonarItem } from "../data/sonar";
import { ItemLink } from "../details/ItemLink";

interface ListViewProps {
  items: SonarItem[];
}

export function ListView({ items }: ListViewProps) {
  if (items.length === 0) {
    return <p>No Sonar items match these filters.</p>;
  }

  const sortedItems = [...items].sort((a, b) => b.number - a.number);

  return (
    <ul className="sonar-list">
      {sortedItems.map((item) => (
        <li key={item.number}>
          <article>
            <h2>
              <ItemLink number={item.number}>
                #{item.number} {item.title}
              </ItemLink>
            </h2>
            <dl className="item-metadata">
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
                    {item.updatedAt.slice(0, 10)}
                  </time>
                </dd>
              </div>
            </dl>

            {item.warnings.length > 0 && (
              <ul aria-label="Warnings" className="warnings">
                {item.warnings.map((warning) => (
                  <li key={`${warning.code}-${warning.status}`}>
                    <span aria-hidden="true">⚠ </span>
                    {warning.message}
                  </li>
                ))}
              </ul>
            )}

            {item.pullRequests.length > 0 && (
              <ul
                aria-label="Supporting pull requests"
                className="pull-requests"
              >
                {item.pullRequests.map((pullRequest) => (
                  <li key={pullRequest.number}>
                    <a href={pullRequest.url}>
                      PR #{pullRequest.number}: {pullRequest.title} (
                      {pullRequest.state})
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </article>
        </li>
      ))}
    </ul>
  );
}

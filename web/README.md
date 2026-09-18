# Tech Sonar web application

```console
npm install
npm run dev
npm test
npm run test:e2e
npm run build
```

Run these commands from `web/`. The development server reads
`public/sonar.json`, a generated fixture committed for local development. The
production workflow replaces this fixture with a current snapshot before
building the application.

The shared controls switch between the visual Sonar and list presentations and
filter both views by category, updated-since date, and status. Selecting an item
opens its details and supporting links.

See the [GitHub issue data model](../docs/github-issue-data-model.md) for the
snapshot's static contract.

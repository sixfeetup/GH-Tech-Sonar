# Tech Sonar web application

Enter the [development environment](../README.md#development-environment)
first; dependencies and Playwright browsers are provisioned automatically.

From the repository root, start the managed development server:

```console
devenv up
```

Open the local URL printed by Vite (normally `http://127.0.0.1:5173`). Stop the
server with Ctrl-C. Vite reloads the application when frontend files change.

To run individual checks, use these commands from `web/` inside the environment:

```console
npm test
npm run test:e2e
npm run build
```

Browser tests start and stop their own server on port 4173, independently of the
managed development server. The development server reads
`public/sonar.json`, a generated fixture committed for local development. The
production workflow replaces this fixture with a current snapshot before
building the application.

The shared controls switch between the visual Sonar and list presentations and
filter both views by category, updated-since date, and status. Selecting an item
opens its details and supporting links.

See the [GitHub issue data model](../docs/github-issue-data-model.md) for the
snapshot's static contract.

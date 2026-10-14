{ pkgs, config, lib, ... }:
let
  packageLock = builtins.fromJSON (builtins.readFile ./web/package-lock.json);
  playwrightVersion = packageLock.packages."node_modules/playwright".version;
  browsers = pkgs.playwright-driver.selectBrowsers {
    withFirefox = false;
    withWebkit = false;
  };
in
{
  assertions = [
    {
      assertion = pkgs.playwright-driver.version == playwrightVersion;
      message = "Nix Playwright ${pkgs.playwright-driver.version} must match npm Playwright ${playwrightVersion}; update the Nix input and npm lockfile together.";
    }
  ];

  packages = [ pkgs.git pkgs.gh ];

  languages.python = {
    enable = true;
    package = pkgs.python314;
    uv.enable = true;
  };

  languages.javascript = {
    enable = true;
    package = pkgs.nodejs_22;
    npm.enable = true;
  };

  env = {
    UV_PYTHON_DOWNLOADS = "never";
    PLAYWRIGHT_BROWSERS_PATH = "${browsers}";
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = "1";
  };

  processes = lib.optionalAttrs (!config.devenv.isTesting) {
    web = {
      exec = "npm run dev -- --host 127.0.0.1";
      cwd = "${config.devenv.root}/web";
    };
  };

  # Initialization tasks are non-fatal in devenv; installation must stop entry.
  enterShell = ''
    uv sync --locked --python "${config.languages.python.package}/bin/python" || exit $?
    source "$UV_PROJECT_ENVIRONMENT/bin/activate"
    (cd "${config.devenv.root}/web" && npm ci) || exit $?
  '';
}

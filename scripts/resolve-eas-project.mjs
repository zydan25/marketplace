const token = process.env.EXPO_TOKEN?.trim();
const owner = process.env.EAS_PROJECT_OWNER?.trim() || "zydan2626";
const slug = process.env.EAS_PROJECT_SLUG?.trim() || "shabik-marketplace";

if (!token) {
  console.error("EXPO_TOKEN is required to resolve the EAS project ID.");
  process.exit(1);
}

const fullName = `@${owner}/${slug}`;
const query = `
  query AppByFullName($fullName: String!) {
    app {
      byFullName(fullName: $fullName) {
        id
        slug
        ownerAccount {
          name
        }
      }
    }
  }
`;

const response = await fetch("https://api.expo.dev/graphql", {
  method: "POST",
  headers: {
    "content-type": "application/json",
    authorization: `Bearer ${token}`,
  },
  body: JSON.stringify({ query, variables: { fullName } }),
});

let payload;
try {
  payload = await response.json();
} catch {
  console.error(`Expo API returned a non-JSON response (HTTP ${response.status}).`);
  process.exit(1);
}

if (!response.ok || payload.errors?.length) {
  console.error(`Unable to resolve EAS project ${fullName}.`);
  if (payload.errors?.length) {
    console.error(payload.errors.map((error) => error.message).join("\n"));
  } else {
    console.error(`HTTP ${response.status}`);
  }
  process.exit(1);
}

const project = payload.data?.app?.byFullName;
const projectId = project?.id?.trim();

if (!projectId) {
  console.error(`No EAS project was found for ${fullName}. Refusing to create a new project automatically.`);
  process.exit(1);
}

if (project.slug !== slug || project.ownerAccount?.name !== owner) {
  console.error("Resolved EAS project does not match the requested owner/slug.");
  console.error(JSON.stringify(project, null, 2));
  process.exit(1);
}

const githubEnv = process.env.GITHUB_ENV;
if (githubEnv) {
  const fs = await import("node:fs/promises");
  await fs.appendFile(githubEnv, `EAS_PROJECT_ID=${projectId}\n`);
}

console.log(`Resolved EAS project ${fullName}: ${projectId}`);

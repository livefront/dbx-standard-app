import { createApp, lakebase, server } from "@databricks/appkit";
import { migrate } from "./db/migrate.ts";

await createApp({
  plugins: [server(), lakebase({ pool: { max: 20 } })],
  // Runs before the server starts listening, so requests never see an unmigrated schema.
  async onPluginsReady(appkit) {
    await migrate(appkit.lakebase.pool);
  },
});

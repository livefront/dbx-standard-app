// Ordered, append-only Postgres migrations for the app-owned `app` schema.
// Never edit a migration that has shipped; add a new one instead.
//
// The app's service principal runs these at startup, so it creates and owns the
// schema. Deploy the app before running it locally, or the schema ends up owned
// by your user and the deployed app can't use it.
//
// Synced gold tables (ticket_facts, customer_features) live in a separate,
// read-only schema managed by Lakebase synced tables; see resources/lakebase.yml.

export interface Migration {
  id: string;
  sql: string;
}

export const migrations: Migration[] = [
  {
    id: "0001_init",
    sql: /* sql */ `
      CREATE SCHEMA IF NOT EXISTS app;

      CREATE OR REPLACE FUNCTION app.set_updated_at() RETURNS trigger AS $$
      BEGIN
        NEW.updated_at = now();
        RETURN NEW;
      END;
      $$ LANGUAGE plpgsql;

      -- Support-team overlay on gold tickets. One row per ticket someone has touched;
      -- the console LEFT JOINs this onto the synced ticket_facts.
      -- priority_override is a human-corrected label for the priority model.
      CREATE TABLE app.ticket_triage (
        ticket_id         BIGINT PRIMARY KEY,
        assignee          TEXT,
        triage_status     TEXT NOT NULL DEFAULT 'new'
                          CHECK (triage_status IN ('new', 'in_progress', 'waiting', 'done')),
        priority_override TEXT CHECK (priority_override IN ('low', 'medium', 'high', 'urgent')),
        notes             TEXT,
        updated_by        TEXT NOT NULL,
        created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
      );
      CREATE TRIGGER ticket_triage_updated_at BEFORE UPDATE ON app.ticket_triage
        FOR EACH ROW EXECUTE FUNCTION app.set_updated_at();

      -- Action items, created by hand, from a Genie answer, or from an approved
      -- agent suggestion. Each one syncs to a Jira DBX Story.
      CREATE TABLE app.action_items (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        ticket_id       BIGINT,
        customer_id     BIGINT,
        title           TEXT NOT NULL,
        description     TEXT,
        source          TEXT NOT NULL CHECK (source IN ('manual', 'genie', 'agent')),
        source_ref      TEXT,
        status          TEXT NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'in_progress', 'done', 'cancelled')),
        assignee        TEXT,
        due_date        DATE,
        -- Jira sync. sync_state: not_synced -> pending -> synced | error.
        jira_key        TEXT UNIQUE,
        jira_status     TEXT,
        jira_updated_at TIMESTAMPTZ,
        sync_state      TEXT NOT NULL DEFAULT 'not_synced'
                        CHECK (sync_state IN ('not_synced', 'pending', 'synced', 'error')),
        sync_error      TEXT,
        last_synced_at  TIMESTAMPTZ,
        created_by      TEXT NOT NULL,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
      );
      CREATE INDEX action_items_ticket_idx ON app.action_items (ticket_id);
      CREATE INDEX action_items_sync_idx ON app.action_items (sync_state)
        WHERE sync_state IN ('pending', 'error');
      CREATE TRIGGER action_items_updated_at BEFORE UPDATE ON app.action_items
        FOR EACH ROW EXECUTE FUNCTION app.set_updated_at();

      -- Every "Suggest" run of the triage agent. proposed_issue is the Jira issue
      -- the agent drafted; nothing is sent to Jira until a person approves it.
      -- status + final_issue are the review record used for agent evaluation.
      CREATE TABLE app.agent_suggestions (
        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        ticket_id           BIGINT NOT NULL,
        current_priority    TEXT,
        predicted_priority  TEXT,
        priority_confidence REAL,
        model_version       TEXT,
        rationale           TEXT,
        proposed_issue      JSONB,
        final_issue         JSONB,
        status              TEXT NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'approved', 'edited', 'rejected', 'failed')),
        action_item_id      UUID REFERENCES app.action_items (id) ON DELETE SET NULL,
        trace_id            TEXT,
        requested_by        TEXT NOT NULL,
        decided_by          TEXT,
        decided_at          TIMESTAMPTZ,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
      );
      CREATE INDEX agent_suggestions_ticket_idx ON app.agent_suggestions (ticket_id, created_at DESC);

      -- Genie tab history and feedback.
      CREATE TABLE app.genie_conversations (
        id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_email            TEXT NOT NULL,
        space_id              TEXT NOT NULL,
        genie_conversation_id TEXT UNIQUE,
        title                 TEXT,
        created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
      );
      CREATE INDEX genie_conversations_user_idx ON app.genie_conversations (user_email, updated_at DESC);
      CREATE TRIGGER genie_conversations_updated_at BEFORE UPDATE ON app.genie_conversations
        FOR EACH ROW EXECUTE FUNCTION app.set_updated_at();

      CREATE TABLE app.genie_messages (
        id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        conversation_id  UUID NOT NULL REFERENCES app.genie_conversations (id) ON DELETE CASCADE,
        genie_message_id TEXT,
        role             TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
        content          TEXT,
        generated_sql    TEXT,
        created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
      );
      CREATE INDEX genie_messages_conversation_idx ON app.genie_messages (conversation_id, created_at);

      CREATE TABLE app.genie_feedback (
        message_id UUID PRIMARY KEY REFERENCES app.genie_messages (id) ON DELETE CASCADE,
        user_email TEXT NOT NULL,
        rating     SMALLINT NOT NULL CHECK (rating IN (-1, 1)),
        comment    TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
      );
    `,
  },
];

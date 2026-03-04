# Build Your Open Brain

## **Complete Setup Guide**

The infrastructure layer for your thinking. One database, one AI gateway, one chat channel. Any AI you use can plug in. No middleware, no SaaS chains, no Zapier.

This isn't a notes app. It's a database with vector search and an open protocol — built so that every AI tool you use shares the same persistent memory of you. Claude, ChatGPT, Cursor, Claude Code, whatever ships next month. One brain. All of them.

---

## **What You're Building**

A Slack channel where you type a thought — it automatically gets embedded, classified, and stored in your database — you get a confirmation reply showing what was captured. Then an MCP server that lets any AI assistant search your brain by meaning.

## **What You Need**

About 45 minutes and zero coding experience. You'll copy and paste everything.

### **Services (All Free Tier)**

- **Supabase** — Your database — stores everything

- **OpenRouter** — Your AI gateway — understands everything

- **Slack** — Your capture interface — where you type thoughts

### **If You Get Stuck**

Follow this guide step by step — it's designed to get you through without outside help. But if something goes sideways, Supabase has a free built-in AI assistant in every project dashboard. Look for the chat icon in the bottom-right corner. It has access to all of Supabase's documentation and can help with every Supabase-specific step in this guide.

Things it's good at:

- Walking you through where to click when you can't find something in the dashboard

- Fixing SQL errors if you paste in the error message

- Explaining terminal commands and what their output means

- Interpreting Edge Function logs when something isn't working

- Explaining Supabase concepts in plain English (what's a service role key? what does Row Level Security do?)

It can't see your screen or run commands for you, but if you paste what you're seeing, it can tell you what to do next.

## **Two Parts**

**Part 1 — Capture** (Steps 1–9): Slack → Edge Function → Supabase. Type a thought, it gets embedded and classified automatically.

**Part 2 — Retrieval** (Steps 10–13): Hosted MCP Server → Any AI. Connect Claude, ChatGPT, or any MCP client to your brain with a URL.

### **After You're Done**

This guide builds the system. The companion prompt pack — [**Open Brain: Companion Prompts**](https://promptkit.natebjones.com/20260224_uq1_promptkit_1) — makes it useful. It includes prompts for migrating your existing AI memories into the brain, discovering use cases specific to your workflow, capture templates that optimize metadata extraction, and a weekly review ritual. Finish the setup first, then grab the prompts.

## **Cost Breakdown**

Service

Cost

Slack

Free

Supabase (free tier)

$0

Embeddings (text-embedding-3-small)

~$0.02 / million tokens

Metadata extraction (gpt-4o-mini)

~$0.15 / million input tokens

For 20 thoughts/day: roughly $0.10–0.30/month in API costs.

---

## **Credential Tracker**

You're going to generate API keys, passwords, and IDs across three different services. You'll need them at specific steps later — sometimes minutes after you create them, sometimes much later. Don't trust your memory.

> ***⚠️ Copy the block below into a text editor (Notes, TextEdit, Notepad) and fill it in as you go. Each item tells you which step generates it.***

View & Copy Code

> ***💡 Seriously — copy that now. You'll thank yourself at Step 7.***

---

# **Part 1 — Capture**

## **Step 1: Create Your Supabase Project**

Supabase is your database. It stores your thoughts as raw text, vector embeddings, and structured metadata. It also gives you a REST API automatically.

1. Go to supabase.com and sign up (GitHub login is fastest)

1. Click **New Project** in the dashboard

1. Pick your organization (default is fine)

1. Set Project name: `open-brain` (or whatever you want)

1. Generate a strong Database password — paste into credential tracker NOW

1. Pick the Region closest to you

1. Click **Create new project** and wait 1–2 minutes

> ***💡 Grab your Project ref — it's the random string in your dashboard URL: ***`supabase.com/dashboard/project/THIS_PART`***. Paste it into the tracker.***

---

## **Step 2: Set Up the Database**

Three SQL commands, pasted one at a time. This creates your storage table, your search function, and your security policy.

### **Enable the Vector Extension**

In the left sidebar: **Database → Extensions** → search for "vector" → flip **pgvector ON**.

### **Create the Thoughts Table**

In the left sidebar: **SQL Editor → New query** → paste and Run:

View & Copy Code

### **Create the Search Function**

New query → paste and Run:

View & Copy Code

### **Lock Down Security**

One more new query:

```plain text
-- Enable Row Level Security
alter table thoughts enable row level security;

-- Service role full access only
create policy "Service role full access"
  on thoughts
  for all
  using (auth.role() = 'service_role');
```

### **Quick Verification**

Table Editor should show the `thoughts` table with columns: id, content, embedding, metadata, created_at, updated_at. Database → Functions should show `match_thoughts`.

---

## **Step 3: Save Your Connection Details**

In the left sidebar: **Settings** (gear icon) → **API**. Copy these into your credential tracker:

- **Project URL** — Listed at the top as "URL"

- **Service role key** — Under "Project API keys" → click reveal

> ***⚠️ Treat the service role key like a password. Anyone with it has full access to your data.***

---

## **Step 4: Get an OpenRouter API Key**

OpenRouter is a universal AI API gateway — one account gives you access to every major model. We're using it for embeddings and lightweight LLM metadata extraction.

Why OpenRouter instead of OpenAI directly? One account, one key, one billing relationship — and it future-proofs you for Claude, Gemini, or any other model later.

1. Go to openrouter.ai and sign up

1. Go to openrouter.ai/keys

1. Click **Create Key**, name it `open-brain`

1. Copy the key into your credential tracker immediately

1. Add $5 in credits under Credits (lasts months)

---

## **Step 5: Create Your Slack Capture Channel**

1. If you don't have a Slack workspace, create one at slack.com (free tier works)

1. Click the **+** next to Channels → **Create new channel**

1. Name it "capture" (or brain, inbox, whatever feels natural)

1. Make it **Private** (recommended — this is personal)

1. Get the Channel ID: right-click channel → View channel details → scroll to bottom (starts with C)

1. Paste the Channel ID into your credential tracker

---

## **Step 6: Create the Slack App**

This is the bridge between Slack and your database.

### **Create the App**

1. Go to api.slack.com/apps → **Create New App** → **From scratch**

1. App Name: "Open Brain", select your workspace

1. Click **Create App**

### **Set Permissions**

1. Left sidebar → **OAuth & Permissions**

1. Scroll to **Scopes → Bot Token Scopes**

1. Add: `channels:history`, `groups:history`, `chat:write`

1. Scroll up → **Install to Workspace** → Allow

1. Copy the **Bot User OAuth Token** (starts with `xoxb-`) into credential tracker

### **Add App to Channel**

In Slack, open your capture channel and type: `/invite @Open Brain`

> ***💡 Don't set up Event Subscriptions yet — you need the Edge Function URL first (Step 7).***

---

## **Step 7: Deploy the Edge Function**

This is the brains of the operation. One function receives messages from Slack, generates an embedding, extracts metadata, stores everything in Supabase, and replies with a confirmation.

> ***💡 New to the terminal? The "terminal" is the text-based command line on your computer. On Mac, open the app called Terminal (search for it in Spotlight). On Windows, open PowerShell. Everything below gets typed there, not in your browser.***

### **Install the Supabase CLI**

> ***💡 Mac users: If you already have Homebrew installed (you'll know — it's the thing you install with ***`brew`***), use the first option. Everyone else: use npm. If you don't have npm either, install Node.js from nodejs.org first — npm comes with it.***

```plain text
# Mac with Homebrew
brew install supabase/tap/supabase
```

```plain text
# Windows, Linux, or Mac without Homebrew
npm install -g supabase
```

### **Log In and Link**

```plain text
supabase login
supabase link --project-ref YOUR_PROJECT_REF
```

Replace `YOUR_PROJECT_REF` with the project ref from your credential tracker (Step 1).

### **Create the Function**

```plain text
supabase functions new ingest-thought
```

Open `supabase/functions/ingest-thought/index.ts` and replace its entire contents with:

View & Copy Code

### **Set Your Secrets**

```plain text
supabase secrets set OPENROUTER_API_KEY=your-openrouter-key-here
supabase secrets set SLACK_BOT_TOKEN=xoxb-your-slack-bot-token-here
supabase secrets set SLACK_CAPTURE_CHANNEL=C0your-channel-id-here
```

> ***💡 SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are automatically available inside Edge Functions — you don't need to set them.***

### **Deploy**

```plain text
supabase functions deploy ingest-thought --no-verify-jwt
```

> ***⚠️ Copy the Edge Function URL immediately after deployment! It looks like: ***`https://YOUR_PROJECT_REF.supabase.co/functions/v1/ingest-thought`

---

## **Step 8: Connect Slack to the Edge Function**

1. Go to api.slack.com/apps → select your Open Brain app

1. Left sidebar → **Event Subscriptions** → toggle **Enable Events ON**

1. Paste your Edge Function URL in the **Request URL** field

1. Wait for the green checkmark ✅ Verified

1. Under **Subscribe to bot events**, add: `message.channels` and `message.groups`

1. Click **Save Changes** (reinstall if prompted)

---

## **Step 9: Test It**

Go to your capture channel in Slack and type:

```plain text
Sarah mentioned she's thinking about leaving her job to start a consulting business
```

Wait 5–10 seconds. You should see a threaded reply:

```plain text
Captured as person_note — career, consulting
People: Sarah
Action items: Check in with Sarah about consulting plans
```

Then open Supabase dashboard → Table Editor → thoughts. You should see one row with your message, an embedding, and metadata.

> ***💡 If that works, Part 1 is done. You have a working capture system.***

---

# **Part 2 — Retrieval**

## **A Quick Note on Architecture**

MCP servers can run two ways: locally on your computer, or hosted in the cloud.

The local approach means installing Node.js, building a TypeScript project, and running a server process on your machine. Every AI client you connect needs the full path to that server plus your database credentials pasted into a config file. If your laptop is closed, your brain is offline. If you switch computers, you set it up again.

We're not doing that.

Your capture system already runs on Supabase — the Edge Function you deployed in Part 1 handles Slack messages without anything running on your computer. The MCP server works the same way. One more Edge Function, deployed to the same project, reachable from anywhere. Your AI clients connect with a URL. No build steps, no local dependencies, no credentials on your machine.

If you want to run locally — maybe you're a developer who prefers that, or you want to customize beyond what Edge Functions allow — the MCP TypeScript SDK with StdioServerTransport works great. The [**Supabase docs on deploying MCP servers**](https://supabase.com/docs/guides/getting-started/byo-mcp) cover both approaches. Everything below uses hosted.

---

## **Step 10: Create an Access Key**

Your MCP server will be a public URL. The Supabase project ref in that URL is random enough that nobody will stumble onto it, but let's close the gap entirely. You'll generate a simple access key that the server checks on every request. Takes 30 seconds.

In your terminal, generate a random key:

```plain text
# Mac/Linux
openssl rand -hex 32
```

```plain text
# Windows (PowerShell)
-join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Maximum 256) })
```

Copy the output — it'll look something like `a3f8b2c1d4e5...` (64 characters). Paste it into your credential tracker under MCP Access Key.

Set it as a Supabase secret:

```plain text
supabase secrets set MCP_ACCESS_KEY=your-generated-key-here
```

---

## **Step 11: Deploy the MCP Server**

One Edge Function. Three tools: semantic search, browse recent thoughts, and stats. Same deployment process as the capture function.

### **Create the Function**

```plain text
supabase functions new open-brain-mcp
```

### **Add Dependencies**

Create `supabase/functions/open-brain-mcp/deno.json`:

```plain text
{
  "imports": {
    "@hono/mcp": "npm:@hono/mcp@0.1.1",
    "@modelcontextprotocol/sdk": "npm:@modelcontextprotocol/sdk@1.24.3",
    "hono": "npm:hono@4.9.2",
    "zod": "npm:zod@4.1.13",
    "@supabase/supabase-js": "npm:@supabase/supabase-js@2.47.10"
  }
}
```

### **Write the Server**

Open `supabase/functions/open-brain-mcp/index.ts` and replace its entire contents with:

View & Copy Code

### **Deploy**

```plain text
supabase functions deploy open-brain-mcp --no-verify-jwt
```

Your MCP server is now live at:

```plain text
https://YOUR_PROJECT_REF.supabase.co/functions/v1/open-brain-mcp
```

Replace `YOUR_PROJECT_REF` with the project ref from your credential tracker (Step 1). Paste the full URL into your credential tracker as the MCP Server URL.

> ***💡 That's it. No npm install, no TypeScript build, no local server to keep running. It's deployed alongside your capture function and runs on Supabase's infrastructure.***

---

## **Step 12: Connect to Your AI**

You need two things from your credential tracker: the MCP Server URL (Step 11) and the access key (Step 10).

### **Claude Desktop**

Settings → Developer → Edit Config:

```plain text
{
  "mcpServers": {
    "open-brain": {
      "type": "http",
      "url": "https://YOUR_PROJECT_REF.supabase.co/functions/v1/open-brain-mcp",
      "headers": {
        "x-brain-key": "your-access-key-from-step-10"
      }
    }
  }
}
```

Restart Claude Desktop. You should see "open-brain" appear in the MCP tools indicator (the hammer icon).

### **Claude Code**

```plain text
claude mcp add open-brain \
  --transport http \
  --url https://YOUR_PROJECT_REF.supabase.co/functions/v1/open-brain-mcp \
  --header "x-brain-key: your-access-key-from-step-10"
```

### **Other Clients (Cursor, VS Code Copilot, ChatGPT Desktop, Windsurf)**

Every MCP-compatible client follows the same pattern: point it at the URL with the `x-brain-key` header. The exact config format varies by client — check their MCP documentation for where to add remote HTTP servers with custom headers.

---

## **Step 13: Use It**

Ask your AI naturally. It picks the right tool automatically:

Prompt

Tool Used

"What did I capture about career changes?"

Semantic search

"What did I capture this week?"

Browse recent

"How many thoughts do I have?"

Stats overview

"Find my notes about the API redesign"

Semantic search

"Show me my recent ideas"

Browse + filter

"Who do I mention most?"

Stats

---

# **Troubleshooting**

If the specific suggestions below don't solve your issue, remember: the Supabase AI assistant (chat icon, bottom-right of your dashboard) can help diagnose problems with anything Supabase-related. Paste the error message and tell it what step you're on.

## **Capture Issues (Part 1)**

### **Slack says "Request URL not verified"**

Your Edge Function isn't deployed or isn't reachable. Run the deploy command again and check the output for errors.

```plain text
supabase functions deploy ingest-thought --no-verify-jwt
```

### **Messages aren't triggering the function**

Check Event Subscriptions — make sure `message.channels` and/or `message.groups` are listed. Verify the app is invited to the channel. Confirm the channel ID in your secrets matches the actual channel.

### **Function runs but nothing in the database**

Check Edge Function logs: Supabase dashboard → Edge Functions → ingest-thought → Logs. Most likely the OpenRouter key is wrong or has no credits.

```plain text
supabase secrets list
```

### **No confirmation reply in Slack**

The bot token might be wrong, or `chat:write` scope wasn't added. Go to your Slack app → OAuth & Permissions and verify. If you added the scope after installing, you need to reinstall the app.

### **Metadata extraction seems off**

That's normal — the LLM is making its best guess with limited context. The metadata is a convenience layer on top of semantic search, not the primary retrieval mechanism. The embedding handles fuzzy matching regardless.

## **Retrieval Issues (Part 2)**

### **AI client says "server disconnected" or tools don't appear**

Check that your URL is exactly right — including `https://` at the start and no trailing slash. The project ref in the URL must match your actual project. Try opening the URL in a browser — you should get an error response (not a 404), which confirms the function is deployed and reachable.

### **Getting 401 errors**

The access key in your AI client config doesn't match what's stored in Supabase secrets. Double-check both values. The header must be `x-brain-key` (lowercase, with the dash).

### **Search returns no results**

Make sure you sent test messages in Part 1 first. Try asking the AI to "search with threshold 0.3" for a wider net. If that still returns nothing, check the Edge Function logs in the Supabase dashboard for errors.

### **Tools work but responses are slow**

First search on a cold function takes a few seconds — the Edge Function is waking up. Subsequent calls are faster. If it's consistently slow, check your Supabase project region — pick the one closest to you.

---

## **How It Works Under the Hood**

When you type a message: Slack sends it to your Edge Function → the function generates an embedding (1536-dimensional vector of meaning) AND extracts metadata via LLM in parallel → both get stored as a single row in Supabase → the function replies in your Slack thread with a summary.

When you ask your AI about it: your AI client sends the query to the MCP Edge Function → the function generates an embedding of your question → Supabase matches it against every stored thought by vector similarity → results come back ranked by meaning, not keywords.

The embedding is what makes retrieval powerful. "Sarah's thinking about leaving" and "What did I note about career changes?" match semantically even though they share zero keywords. The metadata is a bonus layer for structured filtering on top.

### **Swapping Models Later**

Because you're using OpenRouter, you can swap models by editing the model strings in the Edge Function code and redeploying. Browse available models at openrouter.ai/models. Just make sure embedding dimensions match (1536 for the current setup).

---

## **What You Just Built — And What You Can Build Next**

You just used three free services, some copy-pasted code, and a built-in AI assistant to build a personal knowledge system with semantic search and an open protocol. No CS degree. No local servers. No monthly SaaS fee.

Here's the thing worth noticing: that Supabase AI assistant that helped you through the setup? It has access to all of Supabase's documentation, understands your project structure, and can help you build on top of what you've created. That's not a one-time trick for getting unstuck during setup. That's a permanent building partner.

Want to add a new capture source beyond Slack? Ask it how to create another Edge Function. Want to add a new field to your thoughts table? Ask it to help you write the SQL migration. Want to understand how to add authentication so you can share your brain with a teammate? It knows the docs better than you ever will.

You just built AI infrastructure using AI. That pattern doesn't stop here.

---

## **Your Next Step**

Your Open Brain is live. Now make it work for you. The companion prompt pack — [**Open Brain: Companion Prompts**](https://promptkit.natebjones.com/20260224_uq1_promptkit_1) — covers the full lifecycle from here:

- **Memory Migration** — Pull everything your AI already knows about you into your brain so every tool starts with context instead of zero

- **Open Brain Spark** — Personalized use case discovery based on your actual workflow, not generic examples

- **Quick Capture Templates** — Five patterns optimized for clean metadata extraction so your brain tags and retrieves accurately

- **The Weekly Review** — A Friday ritual that surfaces themes, forgotten action items, and connections you missed

Start with the Memory Migration. Then use the Spark to figure out what to capture. The templates build the daily habit. The weekly review closes the loop.

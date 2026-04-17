# Researching Speaking Opportunities

> **Browser automation:** Uses Playwright MCP tools. See `../airtable-config/references/using-playwright-mcp.md`.

Identifies speaking and workshop opportunities near upcoming travel destinations, creates outreach drafts, and tracks deals in BB Airtable.

## What It Does

Five-phase pipeline triggered monthly:

1. **Discover Trips**: Scan TripIt calendar 90 days ahead for upcoming travel
2. **Research Events**: Search for relevant meetups, conferences, and workshops in destination regions
3. **Identify Organizers**: Find organizer contact info, cross-reference BB Airtable
4. **Create Outreach**: Draft personalized emails via gog, create BB Deals
5. **Track Follow-up**: Link deals to tasks, surface in existing deal review

## Event Research via MCP Browser

For each destination region, search event platforms:

### Meetup.com
1. `browser_navigate` → `https://www.meetup.com/find/?keywords=AI+technology&location={city}`
2. `browser_snapshot` → read event listings
3. `browser_evaluate` → `() => window.scrollBy(0, 800)` to load more
4. `browser_snapshot` → extract: event name, date, group name, attendee count, link
5. For promising events, `browser_click` → ref for event link
6. `browser_snapshot` → extract organizer name, description, contact info

### Eventbrite
1. `browser_navigate` → `https://www.eventbrite.com/d/{city}/ai-technology/`
2. `browser_snapshot` → read event listings
3. Extract: event name, date, organizer, venue, link
4. Click through to promising events for organizer details

### Luma
1. `browser_navigate` → `https://lu.ma/discover?location={city}`
2. `browser_snapshot` → read event listings
3. Extract: event name, date, host, link

### LinkedIn Events
1. `browser_navigate` → `https://www.linkedin.com/search/results/events/?keywords=AI+{city}`
2. `browser_snapshot` → read event listings
3. Extract: event name, organizer, date, attendees

### General Discovery
For confs.tech, PaperCall, or general searches, use `browser_navigate` to each URL and `browser_snapshot` to extract event information.

## Speaker Assets

### Bio (Short ~100 words)

Aaron Eden is an AI coach and innovation strategist with 30+ years leading successful teams and startups. He makes artificial intelligence accessible and practical, helping individuals and organizations leverage AI tools so they feel approachable and usable. Aaron runs the AI Trailblazers community, hosts the "AI In Real Life" podcast, and leads an AI Apprenticeship Program focused on equitable access. His philosophy: organizations shouldn't need to be tech giants to benefit from AI innovation. Aaron speaks on AI demystification, enterprise automation, lean innovation, and workforce development.

### Bio (Long ~300 words)

Aaron Eden is an AI coach, innovation strategist, and enterprise leader with over 30 years of experience building and leading successful teams and startups. He specializes in making artificial intelligence accessible and practical -- helping individuals and organizations of all sizes leverage AI tools so they feel more approachable and usable.

Aaron's work spans multiple domains: from robotic process automation and lean innovation methodologies to technology strategy consulting across industries. He runs the AI Trailblazers community, a group dedicated to hands-on education about AI tools and techniques. He hosts the "AI In Real Life" podcast, featuring expert discussions on real-world AI applications. And he leads an AI Apprenticeship Program focused on skillset development and creating opportunities for equitable access to AI capabilities.

As a speaker and workshop facilitator, Aaron brings a rare combination of deep technical understanding and the ability to communicate complex concepts to non-technical audiences. His sessions are practical, interactive, and designed to leave attendees with immediately applicable skills and strategies.

Aaron's philosophy is simple: organizations shouldn't need to be tech giants to access the innovation that AI enables. Whether addressing a room of 20 or 200, his goal is to demystify AI, inspire action, and equip audiences with the tools and confidence to integrate AI into their work and lives.

He speaks on topics including AI demystification for non-technical audiences, enterprise AI strategy and implementation, hands-on AI workshops, lean innovation methodologies, and workforce development through AI apprenticeship models.

### Talk Abstracts

#### 1. AI Demystified: Making AI Approachable for Everyone

**Audience:** Non-technical professionals, business leaders, community groups
**Duration:** 45-60 minutes (talk) or 90 minutes (with Q&A)
**Format:** Keynote / Presentation

AI is everywhere -- but for many, it still feels intimidating and out of reach. This session cuts through the hype and jargon to show what AI actually is, what it can do today, and how anyone can start using it. Through live demonstrations and real-world examples, attendees leave with a clear understanding of AI's practical applications and the confidence to start experimenting on their own.

#### 2. AI for Your Organization: From Strategy to Implementation

**Audience:** Business leaders, executives, operations managers
**Duration:** 60-90 minutes (talk) or half-day (workshop)
**Format:** Keynote / Workshop

Organizations of every size can benefit from AI -- you don't need to be a tech giant. This session walks through a practical framework for identifying AI opportunities, evaluating tools, and implementing solutions that deliver real ROI. From automating repetitive processes to enhancing decision-making, attendees learn how to build an AI strategy that fits their organization's size, budget, and goals.

#### 3. Hands-On AI Workshop: Build Something Real

**Audience:** Anyone curious about AI, from beginners to intermediate users
**Duration:** 2-3 hours (workshop)
**Format:** Interactive Workshop

Stop reading about AI and start using it. This hands-on workshop guides participants through building practical AI-powered solutions using today's most accessible tools. Participants work in small groups to solve real problems -- from content creation and data analysis to process automation. No coding experience required. Attendees leave with working solutions they can immediately apply to their own work.

#### 4. The AI Apprenticeship Model: Building an Equitable AI Workforce

**Audience:** Workforce development leaders, educators, HR professionals, nonprofit leaders
**Duration:** 45-60 minutes (talk) or 90 minutes (panel/discussion)
**Format:** Keynote / Panel

As AI transforms industries, we have a choice: let it widen existing gaps, or use it to create new pathways to opportunity. This session shares lessons from building an AI Apprenticeship Program that combines hands-on training, mentorship, and real-world project experience to develop diverse AI talent. Attendees learn practical strategies for building inclusive AI education programs in their own organizations and communities.

## Outreach Email Templates

### Template 1: Meetup Organizer

```
Subject: Speaking at {event_name} -- AI Workshops & Talks

Hi {organizer_name},

I came across {event_name} and love what you're doing with {group_focus}. I'll be in {city} {travel_dates} and would love to contribute to your community.

I'm an AI coach and speaker who helps make AI accessible and practical. I run the AI Trailblazers community and host the "AI In Real Life" podcast. My sessions are hands-on and designed for {audience_type} audiences.

A few talks that might fit your group:

{relevant_talks}

I'm flexible on format -- happy to do a full talk, lightning talk, workshop, or panel. Would love to chat about what would work best for your group.

You can learn more about my work at aaroneden.com.

Best,
Aaron Eden
```

### Template 2: Conference CFP / Organizer

```
Subject: Speaker Submission -- {conference_name}

Hi {organizer_name},

I'd like to submit a talk for {conference_name}. I'll be in {city} during {travel_dates}, which aligns perfectly with your event.

I'm Aaron Eden -- AI coach, podcast host ("AI In Real Life"), and leader of the AI Trailblazers community. I've spent 30+ years in enterprise tech leadership and now focus on making AI accessible to organizations of all sizes.

Proposed session:

**{talk_title}**
{talk_abstract_short}

I can adapt this to a keynote, breakout session, or workshop format. Happy to discuss what fits your audience best.

More about my work: aaroneden.com

Best,
Aaron Eden
```

### Template 3: Co-working Space / Community Hub

```
Subject: Free AI Workshop for Your Community -- {space_name}

Hi {organizer_name},

I'm an AI coach and community builder, and I'll be in {city} {travel_dates}. I'd love to offer a free hands-on AI workshop for your members at {space_name}.

The workshop is interactive and designed for people at all technical levels. Participants build real solutions using today's AI tools -- no coding required. It's a great way to add value for your community while I'm in town.

I run similar sessions through the AI Trailblazers community and the "AI In Real Life" podcast. Learn more at aaroneden.com.

Would you be open to hosting something? Happy to discuss timing and format.

Best,
Aaron Eden
```

## Event Research Sources

When searching for events in a target region, use these sources:

| Source | What to search | URL pattern |
|--------|---------------|-------------|
| Meetup.com | Tech, AI, innovation, entrepreneur groups | `meetup.com/find/?keywords={topic}&location={city}` |
| Eventbrite | Conferences, workshops, networking events | `eventbrite.com/d/{city}/{topic}` |
| Luma | Tech community events | `lu.ma/discover?location={city}` |
| LinkedIn Events | Professional events and meetups | Search via LinkedIn |
| Confs.tech | Tech conferences | `confs.tech` |
| PaperCall | Open CFPs | `papercall.io/cfps` |
| Perplexity | General event discovery | Search: "upcoming {topic} events in {city} {month} {year}" |

### Relevance Keywords

Search for events matching these themes:
- AI, artificial intelligence, machine learning
- Technology, innovation, digital transformation
- Entrepreneurship, startups, business
- Workforce development, education, training
- Automation, process improvement, lean
- Community, nonprofit, social impact

## Airtable Integration

### Creating a Deal

Use BB Deals table (`tblw6rTtN2QJCrOqf`) in base `appwzoLR6BDTeSfyS`:

| Field | Field ID | Value |
|-------|----------|-------|
| Name | `fldY0uE3xwZLzK0J8` | "{event_name} - Speaking" |
| Status | `fld84ZYnfhVUYbA7f` | "Contacted" |
| Type | `fld4mUh4oUA8VQ3jP` | "New Business" |
| Organization | `fldNbTbG8PjugeCrd` | [org_record_id] |
| Deal Contacts | (via junction table `tblxdCIQQ7Uu0g1qS`) | Create junction record linking deal to contact |
| Assignee | `fldw7L6yCDpT2QBiV` | ["recXgsS1kw8xdSFSW"] (Aaron) |

Campaign field should be set to "Speaking Opps" (verify field ID in Airtable).

### Creating/Updating Contacts

Use BB Contacts table (`tbllWxmXIVG5wveiZ`):
- First search existing contacts via `search-airtable.sh`
- Only create new records if no match found

### Creating/Updating Organizations

Use BB Orgs table (`tblPEqGDvtaJihkiP`):
- First search existing orgs via `search-airtable.sh`
- Only create new records if no match found

## Email Drafting

```bash
# Draft outreach email from aaron@brainbridge.app (BB signature auto-appended)
python3 ../using-gog/scripts/draft_email.py \
  --account bb \
  --to "{organizer_email}" \
  --subject "{subject}" \
  --body "{body}"
```

Use `--no-signature` if the body already includes a sign-off.

## Safety Rules

- **NEVER send emails automatically** -- always create as drafts for Aaron to review
- **NEVER create duplicate contacts/orgs** -- always search first
- **NEVER create duplicate deals** -- check for existing deals with same org/event
- **Always confirm region scope** with Aaron before researching
- **Always present findings** for review before creating deals/drafts

## Cron

Monthly (user will configure). No fixed schedule yet.

## Processed Trips Tracking

To avoid re-processing trips, maintain a state file at:
`maintaining-relationships/data/speaking-opportunities/processed-trips.json`

```json
{
  "processed": [
    {
      "trip_id": "event-uid-from-calendar",
      "destination": "Denver, CO",
      "dates": "2026-03-15 to 2026-03-18",
      "processed_date": "2026-02-16",
      "region_scope": "Front Range Colorado",
      "events_found": 12,
      "outreach_created": 5
    }
  ]
}
```

## Scripts Reference

All scripts live in `scripts/`.

| Script | Purpose |
|--------|---------|
| `fetch_trips.py` | Read TripIt events 90 days ahead via EventKit |
| `search_events.py` | Search for relevant events in a region (web research helper) |
| `create_deal.py` | Create a deal in BB Airtable with linked contact/org |
| `run_pipeline.sh` | Orchestrate the full pipeline |

## Troubleshooting

**No TripIt events found?**
- Verify TripIt syncs to Apple Calendar
- Check `finding-calendar-availability/config.yaml` includes TripIt calendar

**gog draft creation fails?**
- Ensure gog is authenticated: `gog auth status`
- Re-auth if needed: `gog auth add aaron@brainbridge.app --services gmail`

**Airtable errors?**
- Check AIRTABLE_TOKEN is set
- Verify field IDs haven't changed (field IDs are stable, but verify if errors occur)

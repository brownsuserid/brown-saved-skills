# NotebookLM Query Patterns

## Standard Queries by Use Case

### Company Research

| Question | Purpose |
|----------|---------|
| "What is [Company Name] and what do they do?" | Basic company profile |
| "What industry or vertical is [Company] in?" | Market context |
| "What products or services does [Company] offer?" | Offerings overview |
| "Who are [Company]'s main customers or target market?" | Customer profile |
| "What are [Company]'s main business challenges?" | Pain points |
| "What is [Company]'s current growth strategy?" | Business priorities |

### Contact & Stakeholder Research

| Question | Purpose |
|----------|---------|
| "Who is the primary contact at [Company]?" | Main point of contact |
| "What is [Name]'s role and background?" | Contact context |
| "Who are the decision makers at [Company]?" | Buying center |
| "What is [Name]'s contact information?" | Reach-out details |
| "What is [Name]'s professional background?" | Credibility/trust |

### Technical & Tool Stack

| Question | Purpose |
|----------|---------|
| "What tools does [Company] currently use for [function]?" | Current stack |
| "What are the main pain points with their current tools?" | Problems to solve |
| "What integrations are needed?" | Technical requirements |
| "What compliance requirements exist?" | Legal constraints |
| "What is their current workflow or process?" | Operational context |

### Onboarding & Implementation

| Question | Purpose |
|----------|---------|
| "What is the proposed solution or approach?" | Recommended path |
| "What are the phases of implementation?" | Project plan |
| "What are the success metrics or KPIs?" | Outcome measurement |
| "What is the timeline for implementation?" | Scheduling |
| "What resources are needed from each side?" | Resource planning |

### Proposal & Deal Context

| Question | Purpose |
|----------|---------|
| "What was proposed in the [date] proposal?" | Proposal details |
| "What are the pricing tiers or options?" | Commercial terms |
| "What are the next steps from the last meeting?" | Action items |
| "What objections or concerns have been raised?" | Risk factors |
| "What is the current deal status?" | Pipeline position |

## Compliance & Industry-Specific Queries

### Healthcare (HIPAA)

- "What HIPAA compliance requirements does [Company] have?"
- "What safeguards are needed for patient data?"
- "What FDA regulations apply to their products?"

### Finance

- "What financial regulations must [Company] comply with?"
- "What audit requirements exist?"
- "What data security standards are required?"

### Legal

- "What liability concerns does [Company] have?"
- "What contractual obligations exist?"
- "What IP or confidentiality requirements apply?"

## Extracting Structured Data

### Current Stack Documentation

Ask: "List all the tools and systems [Company] currently uses for [function]"

Expected format:
- CRM: [Tool name]
- Email: [Tool name]
- Calendar: [Tool name]
- Lists/Data: [Tool name]
- Communication: [Tool name]

### Pain Point Analysis

Ask: "What are the main problems [Company] is experiencing with their current [system/process]?"

Expected format:
1. [Specific problem] - Impact: [description]
2. [Specific problem] - Impact: [description]

### Requirements Gathering

Ask: "What are the must-have requirements for [Company]'s new [system/solution]?"

Expected format:
- Functional: [requirements]
- Technical: [requirements]
- Compliance: [requirements]
- Integration: [requirements]

## Working with Source Documents

### Identifying Key Sources

Look for these source types in the notebook:
- Proposals (often contain requirements and pricing)
- Meeting recaps (contain decisions and action items)
- Email exchanges (contain context and concerns)
- Research documents (contain background and analysis)

### Source Priorities

1. **Most Recent** - Latest proposals or meeting notes
2. **Most Detailed** - Comprehensive proposals over brief emails
3. **Decision Documents** - Meeting recaps with action items
4. **Background Research** - Perplexity or web research summaries

## Limitations & Workarounds

### When Browser Automation Fails

1. **Ask the user directly** - "Can you tell me what the notebook says about..."
2. **Request a summary** - "Can you copy the notebook's summary for me?"
3. **Access original sources** - Use gog to access Google Docs directly

### When Responses Are Too Long

1. Ask follow-up questions: "Summarize in 3 bullet points..."
2. Request specific sections: "What does the proposal say about pricing?"
3. Break into parts: "First, what tools do they use? Then what are the problems?"

## Integration with Task Execution

### From Notebook to Task

1. Extract requirements → Create task with specific deliverables
2. Extract timeline → Set due dates and milestones
3. Extract contacts → Create contact records
4. Extract tools → Note integrations needed

### From Notebook to Deal

1. Extract proposal details → Update deal value and stage
2. Extract objections → Create follow-up tasks
3. Extract decision makers → Update contact roles
4. Extract timeline → Set close date

## Changelog

| Date | Change |
|------|--------|
| 2026-02-19 | Initial query patterns document |

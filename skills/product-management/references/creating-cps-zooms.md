# Creating CPS Zooms

> **Framework:** Moves the Needle (founded by Aaron Eden)
> **Purpose:** Deep, structured analysis of Customer, Problem, and Solution to sharpen positioning and drive campaign specificity.

A CPS Zoom is not a pitch deck or a one-pager. It is the thinking tool that makes those artifacts precise. Each zoom forces you to articulate who you serve, what they struggle with, and how you solve it at a level of specificity that generic positioning statements never reach.

---

## When to Use

- Launching a new campaign and the ICP/messaging feels vague
- Onboarding a new GTM customer who needs to articulate their positioning
- A product or service has evolved and the old positioning no longer fits
- You need to align a team on who the customer actually is (not who you wish they were)

---

## Workflow

### Step 1: Identify Scope

Ask the user:
- **What product, service, or campaign is this CPS Zoom for?**
- **Is this a new zoom or a revision of an existing one?**

If revising, ask for a link to the existing CPS Zoom doc.

### Step 2: Gather Source Material

Ask the user to point you to source material. Suggest potential sources:

- GTM configuration docs or owner context docs
- Campaign definitions or campaign plan drafts
- Lean Canvas or Critical Assumptions documents
- Pitch decks or proposals
- Meeting transcripts (sales calls, strategy sessions, customer interviews)
- Existing CPS Zooms for other products (as format reference)
- Website copy, landing pages
- Case studies or customer testimonials

**Do not assume sources.** The user decides what is relevant.

### Step 3: Read and Synthesize

Read all provided source material. Extract:
- Who the target customer is (specific, not aspirational)
- What they want to achieve (desired outcomes)
- What stops them (pains at multiple levels)
- What the product/service does about it (mapped to the pains)

### Step 4: Draft the CPS Zoom

Write the full zoom following the template below. Use the prompting questions to fill each section. Where source material is thin, flag the gap explicitly rather than inventing content.

### Step 5: Output

- Create as a **Google Doc** (shared, since this is a team artifact):
  - Title: `CPS Zoom — [Product/Campaign] — V1.0`
  - Use `gog docs create` with the BB account
- Present a summary to the user for review
- Iterate based on feedback

---

## CPS Zoom Template

The three zooms below are the complete structure. Every section must contain real content or an explicit `[GAP: needs X to fill this]` marker. No placeholders. No filler.

---

### 1. Customer Zoom

#### Target Customer

State the target customer in a short, memorable phrase (3-5 words) plus a one-line profile.

Example: "Sophisticated Growth Brands on Amazon" / Profile: Brand Registry qualified; own their IP; >$500k/year GMV; already investing in growth.

*Prompting question: If you had to describe your best customer in one phrase that your whole team would immediately understand, what would it be?*

#### What They Want

List 3-4 desired outcomes. These are what the customer is trying to achieve, not what your product does. Write from their perspective.

*Prompting question: What is your customer trying to achieve or accomplish? What does their ideal state look like?*

#### Qualification

Define how you identify and prioritize these customers in two layers:

**Layer 1: Quantitative (filterable)**
Criteria you can screen for automatically or from data: revenue thresholds, company size, tech stack, industry signals.

**Layer 2: Qualitative (conversational)**
Signals you pick up in conversation: do they respond with recognition or confusion? Have they thought about this problem before? Do they ask sharp questions?

*Prompting question: How do you tell a great-fit customer from a mediocre one? What separates "they get it immediately" from "we have to explain for 30 minutes"?*

*Quality check: Qualification should help you say NO to bad fits, not just YES to good ones.*

#### Unique Attributes

Three traits that make this customer segment distinct from adjacent segments. Each should be a sentence or two explaining not just the trait but why it matters.

*Prompting question: What are three things that are true about your best customers that are NOT true about the broader market?*

*Quality check: If these attributes could describe any company in your industry, they are not specific enough.*

#### Observable Behaviors

3-5 behaviors you can actually see in the wild that identify the target customer. These should be things you could spot from LinkedIn activity, job postings, tool usage, event attendance, or public signals.

*Prompting question: If you were scanning LinkedIn or a conference room, what behaviors would tell you "that person is our customer"?*

---

### 2. Problem Zoom

#### Desired Outcomes

Restate the customer's desired outcomes from the Customer Zoom, but expand each one. What does success look like in concrete terms? What changes in their daily work?

*Prompting question: When this problem is solved, what specifically is different about how they work, decide, or compete?*

#### Pains & Problems

Structure pains in three tiers. This is the core of the Problem Zoom. Each tier goes deeper.

**Tier 1: Felt Pain (What They Experience)**

2-3 pains stated in the customer's own words. Use quoted phrases where possible. These are the symptoms they would describe if you asked "what's frustrating you?"

*Prompting question: What would this customer say if you asked them "what sucks about [this area of their work]?" Use their words, not yours.*

*Quality check: If the customer wouldn't recognize themselves in these statements, rewrite them.*

**Tier 2: Hidden Cost (What It's Actually Costing Them)**

2-3 costs they may not fully quantify. Wasted time, wasted money, missed opportunities, compounding effects. Be specific with estimates where possible.

*Prompting question: What is the dollar, time, or opportunity cost of not solving this? What are they losing that they may not even be tracking?*

**Tier 3: Root Cause (Why They Couldn't Solve It Before)**

2-3 structural reasons this problem persisted until now. Not "they didn't try hard enough" but genuine barriers: technology limitations, information gaps, structural impossibilities, normalized workarounds.

*Prompting question: Why hasn't this been solved already? What changed (or is changing) that makes a solution possible now?*

#### Problem Statement

One paragraph (3-5 sentences) that synthesizes all three tiers into a single coherent statement of the problem. This is the paragraph you could read aloud to a prospect and have them say "yes, exactly."

*Quality check: Read this aloud. Does it flow? Would the customer nod along? Does it make the problem feel urgent without being hyperbolic?*

#### Promise Statement

One paragraph stating the promise you believe you need to make to resolve the pain. This is the bridge between problem and solution. It describes what changes for the customer, not what your product does. It should create the feeling of "I want that."

*Prompting question: What promise, if believed, would make this customer lean forward and say "tell me more"?*

*Quality check: The promise should be specific enough to be falsifiable. "We'll make things better" is not a promise. "You'll see X before Y happens" is.*

---

### 3. Solution Zoom

#### Solution Mapped to Problem Tiers

For each problem tier (Felt Pain, Hidden Cost, Root Cause), state the specific solution capability that addresses it. This creates a direct line from pain to relief.

| Problem Tier | Solution Capability |
|-------------|-------------------|
| Tier 1: [Felt Pain summary] | [What resolves the felt pain] |
| Tier 2: [Hidden Cost summary] | [What eliminates the hidden cost] |
| Tier 3: [Root Cause summary] | [What removes the structural barrier] |

*Quality check: Every problem tier must have a corresponding solution. If a tier has no solution, either the problem is overstated or the solution has a gap.*

#### Top Solution Features

3-5 headline capabilities that deliver the value promised. Each should be a short name followed by a one-sentence description.

*Prompting question: If the customer could only remember 3-5 things about what your product does, what should those be?*

#### By What Means?

The minimum needed to deliver the solution. Cover:

- **Platform**: How is it delivered? (SaaS, service, email, app, etc.)
- **Distribution**: How often and through what channel?
- **Technology**: What powers it? (AI, integrations, proprietary methodology, etc.)
- **Onboarding**: What does getting started require from the customer?
- **Customization**: What can be tailored to each customer's needs?

*Prompting question: What is the simplest true description of how your product works?*

#### Product Capabilities

How the system delivers value at each stage of the customer journey. List 3-6 capabilities in the order the customer encounters them, from first touch to ongoing value.

*Prompting question: Walk me through what happens from the moment a customer signs up to the point where they are getting regular value. What are the key stages?*

#### Speed to Value

What does the customer experience when they first engage? Describe the first-touch experience in 2-3 sentences. This should answer: how quickly do they see proof that this works?

*Prompting question: What is the fastest "aha moment" a new customer can reach? How long does it take?*

*Quality check: If speed to value is measured in months, you may have an onboarding problem worth noting.*

---

## Document History Convention

Each CPS Zoom should end with a version history:

```
Document History
V1.0 (date): Initial CPS Zoom created. [Brief note on key positioning decisions.]
```

Update the history with each revision, noting what changed and why.

---

## Source Attribution

> CPS Zoom Tool, Moves the Needle framework. Founded by Aaron Eden.

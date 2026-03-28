# Architectural Principles for Feature Planning

Think of these as different lenses to look at any problem. A good solution has to look good through all of them, not just one.

## Table of Contents

- [1. Scalability & Operability](#1-scalability--operability-the-what-if-this-succeeds-principle)
- [2. Reliability & Resilience](#2-reliability--resilience-the-what-if-this-breaks-principle)
- [3. Cost Optimization](#3-cost-optimization-the-is-this-worth-it-principle)
- [4. Fitness for Purpose](#4-fitness-for-purpose-the-right-tool-for-the-job-principle)
- [5. Code Health](#5-code-health-the-dont-build-on-a-cracked-foundation-principle)
- [How to Apply Architectural Thinking](#how-to-apply-architectural-thinking)

---

## 1. Scalability & Operability (The "What if this succeeds?" Principle)

This principle forces you to think about the future. It's not just about whether the system can handle more load (technical scalability), but whether we as a team can manage it as it grows (operational scalability).

### Detailed Description

A scalable system can handle growth efficiently. An operable system is easy for humans to build, deploy, monitor, debug, and maintain. A design that is technically scalable but impossible to operate is a failure.

### How to Apply

- Immediately extrapolate your design from current scale to 10x or 100x
- Imagine the pain of your DevOps team trying to deploy an update at scale
- Consider the "resource sprawl" and the difficulty of getting a single view of the system's health when it's fragmented into many pieces
- Think about observability: can we monitor, debug, and understand system behavior easily?

### Questions to Ask

- What happens to this design at 10x the current scale? 100x?
- How would I debug a production issue for one customer at 3 AM?
- How long would it take to deploy a one-line code change across all customers?
- Are we creating a future version of ourselves a lot of extra work?
- Can we get a single view of the system's health, or is it fragmented?
- How easy is it to onboard a new engineer to maintain this?
- What metrics and logs do we need to operate this effectively?

### Structured Logging & Observability

Every feature plan should address how the feature will be observed in production. Structured logging is not optional — it is a core architectural requirement.

**Structured Logging Standards:**
- Use JSON-formatted log output (not plain text) for machine-parseable logs
- Include correlation IDs to trace requests across components and services
- Log key fields consistently: `timestamp`, `level`, `service`, `correlation_id`, `customer_id`, `action`, `latency_ms`, `success`
- Use context managers or decorators to automatically capture timing and success/failure
- Never log sensitive data (PII, credentials, full query content)

**What to log:**
- Every external API call (service, endpoint, latency, status code)
- Every significant business operation (what was done, for whom, how long it took)
- All errors with enough context to reproduce (but not sensitive data)
- State transitions and decision points that affect behavior

**What NOT to log:**
- Credentials, tokens, API keys
- Full request/response bodies containing PII
- High-frequency debug output in production (use log levels appropriately)

**Correlation ID Pattern:**
```
# Generate per-request, propagate through all downstream calls
correlation_id = uuid4().hex[:8]

# Every log entry includes the correlation ID
logger.info("tool_call", extra={
    "cid": correlation_id,
    "tool": "service_name",
    "customer": customer_id,
    "latency_ms": elapsed,
    "success": True,
})
```

**Metrics to plan for:**
- Request count and error rate per operation
- Latency percentiles (P50, P95, P99) per operation
- Business metrics specific to the feature (items processed, queries run, etc.)
- CloudWatch alarms on error rate spikes and latency degradation

---

## 2. Reliability & Resilience (The "What if this breaks?" Principle)

This principle is about designing systems that anticipate and gracefully handle failure. A reliable system does what its users expect it to do. A resilient system stays operational even when its components fail.

### Detailed Description

You should assume that networks will have glitches, APIs will become unavailable, and code will have bugs. The goal is to build a system where these small, inevitable failures don't cause a total outage or data loss.

### How to Apply

- Identify every single point of failure in your design
- Add buffers and shock absorbers (like SQS queues) between components
- Design for graceful degradation: what's the minimal viable service if parts fail?
- Implement retries with exponential backoff for network calls
- Use Dead-Letter Queues (DLQs) for messages that repeatedly fail
- Consider circuit breakers for external service calls

### Questions to Ask

- What is the single point of failure in this system? (If you think there isn't one, look harder)
- If a downstream service is down for 5 minutes, what happens to incoming requests? Do they fail, or do they wait?
- How does the system recover after a failure? Is it automatic or manual?
- Are we using retries with exponential backoff for network calls?
- Do we have Dead-Letter Queues (DLQs) for messages that repeatedly fail?
- What happens if the database is unreachable?
- Can the system detect and route around failures automatically?
- Do we lose data if a component crashes? How do we prevent that?

---

## 3. Cost Optimization (The "Is this worth it?" Principle)

This isn't just about making things cheaper; it's about understanding the Total Cost of Ownership (TCO) and ensuring we get the maximum business value for every dollar spent.

### Detailed Description

TCO includes direct infrastructure costs (what you see on the AWS bill) and indirect operational costs (the engineer-hours needed to maintain it). A design might look cheap on paper but be incredibly expensive to operate.

### How to Apply

- Calculate both direct costs (infrastructure) and indirect costs (maintenance, operations)
- Consider the operational cost of managing complex deployments
- Look for economy of scale opportunities (pooled resources vs. siloed)
- Evaluate if we're paying for idle resources
- Consider the cost of logging, monitoring, and observability
- For AWS infrastructure, use `infra-auditing-aws-spending` skill for detailed cost analysis

### Questions to Ask

- Are we paying for idle resources? (e.g., provisioned throughput we don't use)
- What are the hidden costs of this design? (e.g., engineering time for maintenance, logging/monitoring costs)
- Could we use a cheaper service or a different pattern to achieve the same business outcome?
- Is the cost proportional to the usage/value?
- What are the operational costs (engineer-hours) to maintain this?
- Does this design enable or prevent economy of scale?
- What's the cost impact at 10x scale?

---

## 4. Fitness for Purpose (The "Right tool for the job" Principle)

This principle is about deeply understanding the characteristics of the problem you're solving and choosing technologies and patterns that are a natural fit.

### Detailed Description

Every architectural choice is a trade-off. There is no universally "best" database or "best" messaging service. Kinesis is fantastic for ordered, real-time streaming. Step Functions is fantastic for orchestrating complex, multi-step workflows. They are optimized for different problems.

### How to Apply

- Deeply understand your data characteristics: order, size, frequency, processing speed requirements
- Identify the most critical requirements (e.g., consistency vs. availability)
- Read the "When NOT to use" section of documentation for any technology you're considering
- Consider if you're using a service in a way it wasn't designed for
- Understand the trade-offs you're making explicitly

### Questions to Ask

- What are the most important characteristics of my data? (e.g., order, size, frequency, required processing speed)
- What are the trade-offs I'm making by choosing this service/pattern?
- Am I using a service in a way it wasn't designed for? (e.g., using a database as a message queue)
- Did I read the "When NOT to use" section of the documentation for this technology?
- What am I optimizing for: consistency, availability, partition tolerance, latency, cost, or simplicity?
- Does this technology naturally fit the problem domain?
- What alternative approaches exist, and why are we choosing this one?

---

## 5. Code Health (The "Don't build on a cracked foundation" Principle)

New features don't exist in a vacuum — they're built on top of existing code. This lens ensures you're not propagating existing problems or building on shaky ground.

### Detailed Description

Before adding new code, understand the health of the code you're building on. Existing anti-patterns like error swallowing, tight coupling, or duplicated logic will infect your new feature if you don't address them first. It's cheaper to fix the foundation before building on it than to debug mysterious failures later.

### How to Apply

- Run `dev-reviewing-code` in Deep Scan mode on the areas of code the plan will modify
- Review error handling patterns in existing code — are exceptions being swallowed silently?
- Look for duplication that the new feature would exacerbate
- Check for tight coupling that would make the new feature harder to test
- Decide whether to fix existing issues as part of this plan or explicitly defer them

### Questions to Ask

- Are there existing anti-patterns in the code areas this plan touches?
- Does the existing error handling use narrow exception types and re-raise, or does it swallow errors with broad `except Exception` blocks?
- Is there duplicated logic that the new feature would add to?
- Are the existing tests for this area meaningful, or are they superficial?
- Would adding this feature make existing technical debt worse?
- Should we fix existing issues first, or explicitly document them as out of scope?

---

## How to Apply Architectural Thinking

1. **Always Ask "Why?" and "What if?"**
   - For every component in a design, ask why it's there
   - Ask what if it fails, gets 100x more traffic, or becomes the bottleneck

2. **Think in Trade-offs**
   - Get comfortable with the idea that there is no perfect solution
   - Every decision has a downside
   - Frame decisions like: "We are choosing Pattern A, which gives us lower cost, but we are accepting the trade-off of higher latency"
   - Make trade-offs explicit in your plan

3. **Study Post-Mortems**
   - Learn from major outages and how they were resolved
   - Understand what went wrong and what architectural decisions contributed
   - Apply those lessons to your designs

4. **Consider AWS Well-Architected Framework**
   - Use it as a comprehensive framework for architectural decisions
   - The five pillars: Operational Excellence, Security, Reliability, Performance Efficiency, Cost Optimization

5. **Document Your Reasoning**
   - In your plan, explicitly state why you chose each component
   - Explain what trade-offs you're making and why they're acceptable
   - This helps with review and future maintenance

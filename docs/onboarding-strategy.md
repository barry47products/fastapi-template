# Neighbour Approved - Onboarding Strategy & User Journey

## Executive Summary

Neighbour Approved is an **active assistant** for WhatsApp groups that helps members find trusted local service providers through community endorsements. When someone requests a provider, the bot immediately responds with pre-vetted options from the group's endorsement history. Members simply react with an emoji to receive private contact details.

**Key Value Proposition**: "Get instant recommendations for trusted providers your neighbours have actually used - just tap ⚡ for their details."

## Core Service Flow

### The Magic Moment

```text
Group Member: "Need a good plumber urgently!"
↓
Bot: "Here are plumbers endorsed by this group:
     🔧 Joe's Plumbing (3 endorsements)
     🔧 Premier Plumbing (2 endorsements)
     React 🔧 for contact details"
↓
Member: [Reacts 🔧]
↓
[PRIVATE MESSAGE with phone numbers and reviews]
```

## Phase 1: Discovery & Initial Contact

### How Groups Discover Us

#### **Organic Word-of-Mouth**

- _"Asked for a plumber in our group and immediately got 3 options our neighbours endorsed!"_
- _"Just tap the emoji and you get all their contact details privately"_
- _"No more scrolling through 50 different suggestions"_

#### **Discovery Channels**

1. Adjacent group recommendations
2. Provider referrals ("I'm getting lots of work from Neighbour Approved")
3. Community admin networks
4. Local Facebook groups / Nextdoor mentions

### Initial Admin Contact

#### **Admin's Key Questions**

- "Will this spam our group?"
- "How do you protect privacy?"
- "What if members don't like it?"
- "Can we try it first?"

#### **Our Response Framework**

1. Personal response within 2-4 hours
2. Offer demo group experience
3. Share success metrics from similar groups
4. Emphasize easy removal (just delete contact)
5. Propose listening-only trial period

## Phase 2: The Demo Experience

### Demo WhatsApp Group Setup

Create "Neighbour Approved Demo" group with pre-staged conversations showing:

#### **Example Flow 1: Provider Request**

```text
Alice: "Urgent - need electrician! Kitchen power tripping"

Neighbour Approved: "Here are electricians endorsed by this group:
⚡ Davies Electrical (5 endorsements)
⚡ PowerPro Services (3 endorsements)
React ⚡ to get contact details"

Bob: "Davies is excellent - same day service!"

[Alice reacts ⚡]
```

#### **Example Private Message**

```text
[PRIVATE TO ALICE]
Your requested electrician details:

📞 Davies Electrical
   Phone: 07XXX XXXXXX
   WhatsApp: [Click to chat]
   Endorsed by: Bob, Carol, David, Emma, Frank
   Recent: "Fixed fuse box same day, very professional" - Carol

📞 PowerPro Services
   Phone: 07XXX XXXXXX
   Endorsed by: George, Helen, Ian
   Recent: "Fair pricing, excellent work" - Helen
```

### Admin Trial Experience

1. Admin added to demo group
2. Admin can test making requests
3. Admin experiences emoji reaction flow
4. Admin sees private message with details
5. Admin experiences follow-up endorsement request

## Phase 3: Group Onboarding Process

### Week 1: Silent Listening Period

#### **Day 1-3: Database Building**

- Bot joins group but sends NO messages
- Analyses historical messages for:
  - Provider mentions with endorsements
  - Common service categories
  - Active recommenders
  - Request patterns

#### **Day 4-7: Ready to Assist**

- Internal endorsement database built
- Ready to respond to first request
- Admin privately notified of readiness

### First Live Interaction

#### **Triggering Conditions**

- Someone asks for provider recommendation
- Bot waits 30 seconds for organic responses
- Bot provides endorsed options
- Member uses emoji reaction
- Private details sent

#### **First Group Message Template**

```text
Here are [service] providers endorsed by this group:
[emoji] [Provider Name] ([X] endorsements)
[emoji] [Provider Name] ([X] endorsements)

React [emoji] for contact details
```

### The Endorsement Collection Cycle

#### **Immediate After Request**

- Member receives private contact details
- Details include phone, WhatsApp, recent reviews

#### **2-3 Days Later**

```text
Hi [Name]! How was your experience with [Provider]?

Reply '⭐⭐⭐⭐⭐' for excellent
Reply '❌' if you wouldn't recommend
Reply 'later' to be asked next week
```

#### **After Positive Rating**

```text
Great! Your endorsement helps your neighbours.
[Provider] now has [X] endorsements.

Have you used other [service] providers you'd recommend?
Reply with their name, or 'no' to skip.
```

## Phase 4: Weekly Summary & Viral Loop

### Weekly Digest Format

```text
🏠 [Group Name] Weekly Digest

This week, Neighbour Approved helped with:
• 3 plumber requests (Joe's Plumbing most endorsed)
• 2 electrician requests (Davies Electrical top choice)
• 1 landscaping request (GreenThumb recommended)

New endorsements added:
⭐ AquaFix Plumbing (Jane - "excellent service")
⭐ Bright Spark Electric (Tom)

Need a service? Just ask in the group!
```

### Creating Viral Moments

#### **Success Indicators**

- Public thank you in group: _"This is brilliant!"_
- Provider feedback: _"Getting lots of work from your group"_
- Cross-group referral: _"You need this in your group too"_

## Manual Validation Playbook (Weeks 1-4)

### Week 1-2: Friends & Family (5 Groups)

#### **Daily Operations**

- **Morning**: Review overnight messages in all groups
- **Afternoon**: Process requests, prepare responses
- **Evening**: Send private endorsement follow-ups
- **Track**: Response rates, emoji reactions, endorsements

#### **Learning Objectives**

- Optimal response timing (immediate vs 30-second delay)
- Best emoji choices per service type
- Message wording that maximizes reactions
- Follow-up timing for endorsements

### Week 3-4: First Real Communities

#### **Selection Criteria**

- Active groups (50+ messages/week)
- Engaged admin who provides feedback
- Geographic clustering for network effects
- Mix of group sizes (100-500 members)

#### **Metrics to Track**

| Metric | Target | Actual |
|--------|--------|--------|
| Request Detection Rate | 95% | Track |
| Emoji Reaction Rate | 40% | Track |
| Endorsement Completion | 30% | Track |
| Public Thank Yous | 2/week | Track |
| Admin Satisfaction | 8/10 | Track |

### Success Criteria for Full Launch

#### **Quantitative Metrics**

- 4/5 groups retain service after 2 weeks
- 40%+ emoji reaction rate on bot responses
- 30%+ complete endorsement follow-ups
- 1+ organic referral per week

#### **Qualitative Indicators**

- Zero spam complaints
- Multiple public endorsements of service
- Provider reports increased business
- Admin recommends to other groups

## Technical Implementation Phases

### Phase 1: Manual Operations (Weeks 1-2)

- Personal WhatsApp Business account
- Spreadsheet tracking
- Manual message sending
- Manual endorsement tracking

### Phase 2: Semi-Automated (Weeks 3-4)

- NLP for request detection
- Database for endorsements
- Templated responses
- Manual verification before sending

### Phase 3: Supervised Automation (Week 5+)

- Full GREEN-API integration
- Automated request detection
- Automated response generation
- Daily manual review and optimization

## Service Differentiation

### What Makes Us Different

#### **Not Just Tracking Mentions**

- Only shows ENDORSED providers
- Validates through actual usage
- Builds trust through experience

#### **Active Assistance Model**

- Responds immediately to requests
- Provides organized options
- Delivers private contact details
- Follows up for quality assurance

#### **Network Effects**

- Groups benefit from nearby endorsements
- Providers build area-wide reputation
- Trust compounds across communities

## Risk Mitigation

### Potential Issues & Responses

#### **"It's Spamming Our Group"**

- Implement quiet hours
- Reduce summary frequency
- Increase response delay
- Offer immediate removal

#### **"Privacy Concerns"**

- Explain data handling clearly
- Show what's stored (only endorsements)
- Provide data deletion option
- Never share across groups without permission

#### **"Not Enough Providers"**

- Seed from nearby groups
- Lower endorsement threshold initially
- Encourage historical endorsements
- Focus on most-requested categories

## Scaling Strategy

### Geographic Rollout Plan

#### **Month 1: Proof of Concept**

- 5 friendly test groups
- Single neighbourhood focus
- Manual operations
- Refine core flow

#### **Month 2: Neighbourhood Saturation**

- 20 groups in same area
- Create density for network effects
- Semi-automated operations
- Provider engagement begins

#### **Month 3: Adjacent Expansion**

- 50 groups across 3 neighbourhoods
- Full automation with supervision
- Provider dashboard development
- Viral growth mechanics

## Appendix: Message Templates

### Welcome Message

```text
👋 Hi [Group Name]!

I'm here to help you find trusted local providers through your group's recommendations.

When someone needs a service, I'll share endorsed options from your community. React with an emoji to get contact details privately.

Currently in listening mode - learning your group's trusted providers.

Your privacy matters: I only track public endorsements, never personal conversations.
```

### First Request Response

```text
Here are [service] providers endorsed by this group:
[emoji] [Provider 1] ([X] endorsements)
[emoji] [Provider 2] ([X] endorsements)

React [emoji] for contact details
Still looking? Others may add suggestions below!
```

### Private Details Message

```text
Your requested [service] details:

📞 [Provider Name]
   Phone: [Number]
   WhatsApp: [Click to chat]
   Endorsed by: [Names]
   Recent: "[Review]" - [Name]

After using them, let me know how it went!
Your feedback helps your neighbours.
```

### Admin Check-in

```text
Weekly Admin Update - [Group Name]:

Requests Handled: [X]
Members Helped: [X]
New Endorsements: [X]
Reaction Rate: [X]%

Top Provider: [Name] ([X] endorsements)

Any concerns? Reply here or remove the bot anytime.
Thank you for trusting Neighbour Approved!
```

## Key Success Principles

1. **Value First**: Demonstrate immediate utility with first interaction
2. **Trust Through Transparency**: Clear about what we do and don't do
3. **Frictionless Experience**: Emoji reactions remove all barriers
4. **Private When Needed**: Contact details always stay private
5. **Community-Driven**: Groups build their own trusted network
6. **Continuous Improvement**: Every interaction teaches us something

---

_This document is a living strategy guide. Update based on learnings from each manual validation phase._

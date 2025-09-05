# Neighbour Approved: Product Strategy & LEAN Roadmap

## Product-Market Fit Analysis

### The Problem-Solution Fit

#### Problem Validation Signals

- "Anyone know a good plumber?" appears in 73% of neighbourhood WhatsApp groups weekly
- Same questions repeated average 4.2 times per month
- 89% of recommendations lost in chat history within 48 hours
- Zero retention of community knowledge for new members

#### Solution Validation

- No behaviour change required (stays in WhatsApp)
- Automatic value capture (recommendations → endorsements)
- Visible impact (group summaries show accumulated wisdom)
- Natural viral mechanics (emoji reactions, adjacent groups)

### Market Segmentation

#### Primary Market: UK Neighbourhood WhatsApp Groups

- 12M UK households in WhatsApp groups
- Average group size: 50-150 members
- 3-5 service requests per group per week
- £12B annual spend on home services

#### Beachhead Market: London Suburban Communities

- High smartphone penetration
- Active WhatsApp group culture
- Premium home service spending
- Dense neighbourhood networks

#### Expansion Markets

1. Parent WhatsApp groups (school runs, PTAs)
2. Hobby/interest groups (sports clubs, churches)
3. Professional networks (co-working spaces)
4. International markets (India, Brazil, South Africa)

### The Value Metric

#### For Communities: Time saved finding trusted services

- Before: 2-3 hours researching + risk of poor service
- After: 30 seconds to see endorsed providers
- Value: £50-200 saved per poor contractor avoided

#### For Providers: Cost per qualified lead

- Current: £30-50 via Google Ads (cold leads)
- Neighbour Approved: £5-10 (warm, endorsed leads)
- 5-10x ROI improvement

---

## LEAN Startup Approach - Flow-Based

### Build-Measure-Learn Cycles (No Timelines)

#### WIP Limit 1: Complete one cycle before starting the next

#### Cycle 1: Problem Validation

##### Build: Manual process

- Join 5 test WhatsApp groups
- Manually track recommendations
- Create spreadsheet of providers mentioned

##### Measure

- Frequency of service requests
- Recommendation patterns
- Provider overlap between requests
- Message volume and timing

##### Learn

- Validate problem exists
- Understand natural language patterns
- Identify peak activity times
- Confirm providers get mentioned multiple times

##### Decision Gate: Do groups repeatedly ask for same services? YES → Proceed

#### Cycle 2: Solution Validation

##### Build: Manual MVP

- Human operator monitoring groups
- Manual message sending for summaries
- Google Sheets for tracking endorsements
- Manual emoji reaction monitoring

##### Measure (Cycle 2)

- Engagement with summaries
- Emoji reaction rate
- Follow-up endorsement rate
- Opt-out rate

##### Learn (Cycle 2)

- Message format preferences
- Optimal summary frequency
- Privacy sensitivity levels
- Value perception

##### Decision Gate: Do groups engage with summaries? >20% reaction rate → Proceed

#### Cycle 3: Automation MVP

##### Build: Basic bot

- Keyword detection for requests
- Auto-capture recommendations
- Scheduled summary posting
- Semi-automated emoji handling

##### Measure (Cycle 3)

- Classification accuracy
- Provider deduplication success
- System reliability
- User satisfaction (NPS)

##### Learn (Cycle 3)

- Technical edge cases
- Natural language variations
- Scaling bottlenecks
- Support requirements

##### Decision Gate (Cycle 3): Can we automate 80% accurately? YES → Scale

#### Cycle 4: Monetisation Test

##### Build: Payment layer

- Provider dashboard (basic)
- Keyword bidding system (manual)
- Payment integration
- ROI tracking

##### Measure (Cycle 4)

- Provider willingness to pay
- Keyword pricing tolerance
- Lead quality scores
- Retention rates

##### Learn (Cycle 4)

- Pricing sweet spots
- Feature requirements for payment
- Provider success metrics
- Churn indicators

##### Decision Gate (Cycle 4): Can we achieve >£1000 MRR? YES → Full product

---

## Minimum Viable Product (MVP) Definition

### MVP Scope: The "Concierge Bot"

#### Core Features

1. **Request Detection**: Identify when someone asks for a service
2. **Recommendation Capture**: Track provider mentions
3. **Automatic Endorsement**: Second mention = endorsement
4. **Daily Summary**: Post endorsed providers once daily
5. **Emoji Reactions**: Send contacts to those who react
6. **Follow-up Message**: Ask original requester about endorsement

#### Explicitly Excluded from MVP

- Provider self-service
- Payment processing
- Multi-language support
- Advanced NLP
- Analytics dashboard
- White-label options

#### Success Criteria

- 10 active groups
- 100 providers tracked
- 50 endorsements created
- 20% emoji reaction rate
- <5% opt-out rate

---

## Product Roadmap - Flow-Based Sequential Development

### Phase 0: Manual Validation ✓ COMPLETE FIRST

#### "Wizard of Oz" Testing

_Features_:

- Human-powered monitoring
- Manual message sending
- Spreadsheet tracking

_Success Metrics_:

- 5 groups onboarded
- 50 recommendations tracked
- 10 endorsements created

#### GATE: Manual process validated → Move to Phase 1

### Phase 1: MVP Bot ✓ THEN

#### **"Automated Concierge"**

_Features_:

- Automated request detection
- Recommendation extraction
- Summary generation
- Emoji reaction handling
- Basic follow-up system

_Success Metrics_:

- 50 groups onboarded
- 500 providers in system
- 200 endorsements
- 1 group referring another

#### GATE: Core automation working → Move to Phase 2

### Phase 2: Intelligence Layer ✓ THEN

#### **"Smart Assistant"**

_Features_:

- NLP for better classification
- Fuzzy provider matching
- Category taxonomy
- Personalised summaries
- A/B testing framework

_Success Metrics_:

- 200 groups
- 2000 providers
- 30% emoji reaction rate
- <2% error rate

#### GATE: Accuracy at 95% → Move to Phase 3

### Phase 3: Provider Platform ✓ THEN

#### **"Two-Sided Marketplace"**

_Features_:

- Provider dashboard
- Claim your profile
- Keyword bidding (limited)
- Lead tracking
- ROI analytics

_Success Metrics_:

- 50 paying providers
- £5000 MRR
- 80% provider retention
- 10% lead conversion

#### GATE: Revenue model proven → Move to Phase 4

### Phase 4: Scale & Expand ✓ THEN

#### **"Network Effects"**

_Features_:

- Multi-region support
- Advanced bidding system
- Provider verification
- Community insights
- API for enterprises

_Success Metrics_:

- 1000 groups
- 200 paying providers
- £25,000 MRR
- 3 new cities

#### GATE: Scalability proven → Move to Phase 5

### Phase 5: Platform Evolution ✓ FINALLY

#### "Ecosystem"

_Features_:

- White-label offering
- Insurance partnerships
- Booking integration
- Review aggregation
- AI-powered matching

_Success Metrics_:

- 10,000 groups
- £250,000 MRR
- 2 enterprise clients
- Category leader position

**Note**: Each phase must be COMPLETELY finished before starting the next. No parallel work, no jumping ahead.

---

## Key Performance Indicators (KPIs)

### North Star Metric

**Monthly Active Endorsed Providers** - Providers with at least one endorsement who received at least one lead this month

### Leading Indicators

#### Activation Metrics

- Groups with first summary posted
- Time to first emoji reaction
- First endorsement created

#### Engagement Metrics

- Weekly active groups
- Emoji reaction rate
- Endorsement conversion rate
- Summary view rate

#### Viral Metrics

- Group-to-group referral rate
- Provider mention velocity
- Endorsement accumulation rate
- Network density (providers per group)

### Lagging Indicators

#### Revenue Metrics

- Monthly Recurring Revenue (MRR)
- Average Revenue Per Provider (ARPP)
- Customer Acquisition Cost (CAC)
- Lifetime Value (LTV)

#### Quality Metrics

- Provider satisfaction (NPS)
- Group admin satisfaction
- Lead quality score
- Endorsement authenticity rate

---

## Risk Mitigation & Pivots

### Identified Risks & Mitigations

#### Risk 1: WhatsApp Policy Violation

- Mitigation: Strict compliance, legal review
- Pivot: Direct WhatsApp Business API partnership

#### Risk 2: Low Group Adoption

- Mitigation: Manual onboarding, success stories
- Pivot: Focus on group admins as champions

#### Risk 3: Provider Apathy

- Mitigation: Free tier, proven ROI examples
- Pivot: Lead generation model vs subscription

#### Risk 4: Recommendation Fraud

- Mitigation: Velocity checks, admin controls
- Pivot: Verified provider programme

### Pivot Triggers

#### When to Pivot

- <10% group engagement after 3 months
- <5% provider conversion after 100 leads
- > 20% opt-out rate sustained
- CAC > 3x LTV

#### Potential Pivots

1. **Admin Tool Pivot**: Sell to group admins as management tool
2. **Lead Gen Pivot**: Pure lead generation, no endorsements
3. **Data Play Pivot**: Aggregate insights for providers
4. **White-Label First**: Enterprise before consumer

---

## Experimentation Framework

### A/B Testing Priority

#### Phase 1 Tests

1. Summary frequency (daily vs bi-weekly)
2. Message format (list vs cards)
3. Emoji choice (👍 vs ⚡ vs 📞)
4. Follow-up timing (3 days vs 7 days)

#### Phase 2 Tests

1. Endorsement thresholds for visibility
2. Provider information depth
3. Category organisation
4. Personalisation level

### Hypothesis Documentation

#### Template

```text
Hypothesis: [We believe that...]
Test: [We will test by...]
Metric: [We will measure...]
Success: [We will know we're right if...]
```

#### Example

```text
Hypothesis: We believe that emoji reactions increase engagement
Test: We will test by comparing emoji vs text responses
Metric: We will measure response rate
Success: We will know we're right if emoji > 2x text rate
```

---

## Go-to-Market Strategy

### Launch Sequence

#### Week 1-2: Friends & Family

- 5 friendly groups
- Manual operation
- Rapid iteration

#### Week 3-4: Local Hero

- Target one neighbourhood completely
- Create density for network effects
- Document success stories

#### Week 5-8: City Expansion

- Expand through adjacent neighbourhoods
- Leverage referrals
- PR push with local media

#### Week 9-12: Multi-City

- Replicate playbook
- Remote onboarding
- Standardised operations

### Growth Loops

#### Primary Loop: Viral Group Spread

1. Group A succeeds with platform
2. Members belong to other groups
3. They request platform in Group B
4. Group B onboards
5. Repeat

#### Secondary Loop: Provider Success

1. Provider gets endorsed
2. Delivers great service
3. Gets more endorsements
4. Becomes "Local Legend"
5. Tells other providers
6. They want in

#### Tertiary Loop: New Resident Onboarding

1. New resident joins group
2. Sees summary of endorsed providers
3. Uses provider successfully
4. Adds endorsement
5. Increases platform value

---

## Success Definition

### Milestone-Based Success (Not Time-Based)

#### Milestone 1: Problem-Solution Fit

- Manual process validated with 5 groups
- Clear evidence of repeated problem
- Users engage with manual solution
- Ready to automate

#### Milestone 2: Product-Market Fit

- 50 active WhatsApp groups
- 25% week-on-week growth achieved
- <2% monthly churn
- Users actively recommending to other groups

#### Milestone 3: Revenue Validation

- £10,000 MRR achieved
- CAC < LTV validated
- 80% provider retention
- Proven unit economics

#### Milestone 4: Scale Validation

- 500 active groups
- System handling load efficiently
- Operations largely automated
- Ready for geographic expansion

#### Milestone 5: Market Leadership

- 5,000 active groups
- £100,000 MRR
- Recognised brand in category
- Strategic acquisition interest

### Key Learning Questions (Answer Sequentially)

**First**: What triggers groups to adopt?
**Then**: What's the optimal summary frequency?
**Then**: How do providers discover they're listed?
**Then**: What makes providers pay?
**Then**: Which categories monetise best?
**Then**: Can we expand beyond home services?
**Finally**: Should we build or partner for payments?

### The LEAN Mindset

**Build**: Only what tests the riskiest assumption
**Measure**: What matters for the next decision
**Learn**: Until you have clear answers
**Pivot**: When data contradicts assumptions
**Persevere**: When metrics show traction

Remember: **The goal isn't speed. It's learning what works, then scaling what's proven.**

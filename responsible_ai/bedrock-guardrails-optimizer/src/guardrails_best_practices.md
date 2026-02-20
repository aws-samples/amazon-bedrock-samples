# Amazon Bedrock Guardrails Best Practices

This document summarizes best practices from AWS documentation and blogs for optimizing Bedrock Guardrails configurations.

## Denied Topics Best Practices

### Topic Definition Guidelines
1. **Be crisp and precise** - A clear and unambiguous topic definition improves detection accuracy
   - Good: "Questions or information associated with investing, selling, transacting, or procuring cryptocurrencies"
   - Bad: "Crypto stuff" (too vague)

2. **Don't include instructions** - Topic definitions should describe content, not actions
   - Good: "Investment advice including inquiries, guidance, or recommendations about fund management"
   - Bad: "Block all contents associated to cryptocurrency" (this is an instruction)

3. **Don't define negative topics or exceptions**
   - Bad: "All contents except medical information"
   - Bad: "Contents not containing medical information"

4. **Don't use topics to capture entities or words** - Use word filters instead
   - Bad: "Statements containing the name of person X"
   - Bad: "Statements with competitor name Y"
   - Topics represent themes/subjects evaluated contextually, not keyword matching

5. **Topic names should be nouns or phrases** - Don't describe the topic in the name
   - Good: "Investment Advice"
   - Bad: "Block investment advice questions"

### Topic Definition Structure
- **Name**: Noun or short phrase (e.g., "Investment Advice")
- **Definition**: Up to 200 characters summarizing the topic and subtopics
- **Sample phrases**: Up to 5 examples, each up to 100 characters (optional but recommended)

## Safeguard Tiers

### Standard Tier Benefits (Recommended)
- 30% improvement in recall for content filters
- 16% gain in balanced accuracy for content filters
- 32% increase in recall for denied topic detection
- 18% improvement in balanced accuracy for denied topics
- Enhanced robustness against prompt typos and manipulated inputs
- Support for 60+ languages
- Code domain support for content filters and denied topics
- Requires cross-region inference opt-in

### Classic Tier
- Lower latency
- Supports English, French, Spanish
- Original behavior

## Content Filters Configuration

### Filter Strength Levels
- **NONE**: No filtering
- **LOW**: Blocks HIGH confidence harmful content only
- **MEDIUM**: Blocks HIGH and MEDIUM confidence content
- **HIGH**: Blocks HIGH, MEDIUM, and LOW confidence content (most aggressive)

### Recommended Settings by Category
- **HATE**: HIGH (block all hate speech)
- **INSULTS**: MEDIUM (balance between blocking and false positives)
- **SEXUAL**: HIGH (block all sexual content)
- **VIOLENCE**: HIGH (block all violent content)
- **MISCONDUCT**: HIGH (block illegal/harmful activities)
- **PROMPT_ATTACK**: HIGH for input, NONE for output (detect injection attempts)

## Word Filters Best Practices

### When to Use Word Filters
- Exact match blocking for specific terms
- Competitor names
- Profanity and offensive terms
- Specific entity names that should always be blocked

### Limitations
- Exact match only (no fuzzy matching)
- Use for specific terms, not themes/concepts
- Combine with denied topics for comprehensive coverage

## Optimization Strategy

### Iterative Approach
1. Start with baseline configuration
2. Test against representative data
3. Analyze false positives (legitimate content blocked)
4. Analyze false negatives (harmful content allowed)
5. Refine topic definitions based on patterns
6. Add word filters for specific terms causing issues
7. Adjust content filter strengths if needed
8. Re-test and iterate

### Reducing False Positives
- Make topic definitions more specific
- Add exclusion context in definitions (e.g., "medical advice, NOT including IT system health")
- Use sample phrases that clarify boundaries
- Lower content filter strength if too aggressive

### Reducing False Negatives
- Add new denied topics for uncovered categories
- Add word filters for specific terms
- Increase content filter strength
- Add more sample phrases to existing topics
- Make topic definitions broader (carefully)

## Defense in Depth

### Layered Security Approach
1. **Content filters**: First line of defense for harmful content categories
2. **Prompt attack detection**: Catch injection and jailbreak attempts
3. **Denied topics**: Block application-specific unwanted content
4. **Word filters**: Exact match for specific blocked terms
5. **Sensitive information filters**: Protect PII and custom patterns

### Encoding Attack Protection (Standard Tier)
- Standard tier detects encoded content (base64, hex, ROT13, etc.)
- Enable prompt attack filter for encoded output requests
- Consider zero-tolerance encoding detection for high-security environments

## Testing Best Practices

1. **Use representative test data** - Include edge cases and boundary conditions
2. **Test both inputs and outputs** - Guardrails can be applied to both
3. **Monitor false positive/negative rates** - Track accuracy metrics
4. **Iterate based on real-world usage** - Refine after deployment
5. **Use ApplyGuardrail API for testing** - Test without model invocation

## Common Pitfalls to Avoid

1. **Overly broad topic definitions** - Causes false positives
2. **Using topics for keyword matching** - Use word filters instead
3. **Negative definitions** - Don't define what NOT to block
4. **Instructions in definitions** - Describe content, not actions
5. **Ignoring Standard tier benefits** - Use Standard for better accuracy
6. **Not using sample phrases** - They improve detection accuracy
7. **Setting all filters to HIGH** - May cause excessive false positives

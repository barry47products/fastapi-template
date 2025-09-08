# Functional Programming Pocket Guide

## What Is Functional Programming?

Functional programming (FP) is a programming paradigm where you build programmes by composing **pure functions**, avoiding **shared state**, **mutable data**, and **side effects**. Think of it as programming with mathematical functions—given the same input, you always get the same output.

## Core Principles

### 1. Immutability

**Don't change things; create new things instead.**

```javascript
// ❌ Imperative (mutating)
let numbers = [1, 2, 3];
numbers.push(4); // Changed the original array

// ✅ Functional (immutable)
const numbers = [1, 2, 3];
const newNumbers = [...numbers, 4]; // Created a new array
```

### 2. Pure Functions

**Functions that:**

- Always return the same output for the same input
- Have no side effects (don't modify external state)

```javascript
// ❌ Impure function
let total = 0;
function addToTotal(value) {
  total += value; // Modifies external state
  return total;
}

// ✅ Pure function
function add(a, b) {
  return a + b; // No external dependencies
}
```

### 3. Function Composition

**Build complex operations by combining simple functions.**

```javascript
// Small, focused functions
const double = (x) => x * 2;
const addOne = (x) => x + 1;

// Compose them
const doubleThenAddOne = (x) => addOne(double(x));
// doubleThenAddOne(3) → 7
```

### 4. Higher-Order Functions

**Functions that take or return other functions.**

```javascript
// map, filter, reduce are higher-order functions
const numbers = [1, 2, 3, 4, 5];

const doubled = numbers.map((x) => x * 2); // [2, 4, 6, 8, 10]
const evens = numbers.filter((x) => x % 2 === 0); // [2, 4]
const sum = numbers.reduce((acc, x) => acc + x, 0); // 15
```

## Recognising Functional vs Imperative Code

### Imperative Style (How to do it)

```javascript
function getAdultNames(users) {
  const names = [];
  for (let i = 0; i < users.length; i++) {
    if (users[i].age >= 18) {
      names.push(users[i].name.toUpperCase());
    }
  }
  return names;
}
```

### Functional Style (What to do)

```javascript
const getAdultNames = (users) =>
  users.filter((user) => user.age >= 18).map((user) => user.name.toUpperCase());
```

## Key Patterns to Practice

### 1. Replace Loops with Map/Filter/Reduce

**Map**: Transform each element

```javascript
// Instead of:
const results = [];
for (const item of items) {
  results.push(transform(item));
}

// Use:
const results = items.map(transform);
```

**Filter**: Select elements that match criteria

```javascript
// Instead of:
const results = [];
for (const item of items) {
  if (condition(item)) {
    results.push(item);
  }
}

// Use:
const results = items.filter(condition);
```

**Reduce**: Combine elements into a single value

```javascript
// Instead of:
let total = 0;
for (const num of numbers) {
  total += num;
}

// Use:
const total = numbers.reduce((sum, num) => sum + num, 0);
```

### 2. Avoid Mutations

```javascript
// Adding to object
const updatedUser = { ...user, name: "New Name" };

// Adding to array
const newItems = [...items, newItem];

// Removing from array
const filtered = items.filter((item) => item.id !== targetId);

// Updating array element
const updated = items.map((item) =>
  item.id === targetId ? { ...item, done: true } : item
);
```

### 3. Currying and Partial Application

Break functions into smaller, reusable pieces:

```javascript
// Curried function
const multiply = (a) => (b) => a * b;

const double = multiply(2);
const triple = multiply(3);

double(5); // 10
triple(5); // 15
```

### 4. Function Pipelines

Chain operations in a readable way:

```javascript
// Using a pipe helper
const pipe =
  (...fns) =>
  (x) =>
    fns.reduce((v, f) => f(v), x);

const processData = pipe(parseInput, validate, transform, format);

const result = processData(rawData);
```

## Mental Shifts

### Think in Transformations

Instead of "change this variable", think "create a new version with this change".

### Think in Flows

Data flows through a series of transformations, like water through pipes.

### Think Declaratively

Describe **what** you want, not **how** to get it step-by-step.

### Embrace Small Functions

Each function does one thing well. Complex behaviour emerges from composition.

## Common Pitfalls to Avoid

1. **Forgetting immutability**: Always create new objects/arrays rather than modifying existing ones
2. **Hidden side effects**: Watch out for console.log, API calls, or DOM manipulation in functions
3. **Overcomplicating**: Start simple—not everything needs to be curried or composed
4. **Performance paranoia**: Modern JavaScript engines optimise functional code well; prioritise readability first

## Practice Exercises

1. **Refactor a loop**: Take any for-loop in your code and rewrite it using map, filter, or reduce
2. **Pure function challenge**: Write a shopping cart total calculator using only pure functions
3. **Compose utilities**: Create small utility functions and compose them to solve a larger problem
4. **Immutable updates**: Practice updating nested objects without mutation

## Quick Reference Checklist

When writing functional code, ask yourself:

- [ ] Can this function be pure?
- [ ] Am I modifying data or creating new data?
- [ ] Can I replace this loop with map/filter/reduce?
- [ ] Is this function doing just one thing?
- [ ] Can I compose smaller functions to achieve this?

## Language-Specific Notes

### Python

- List comprehensions are often more Pythonic than map/filter
- Use `functools` for partial application and reduce
- Consider `itertools` for lazy evaluation
- Tuples are immutable; prefer them over lists when data shouldn't change
- Use `frozenset` for immutable sets

### JavaScript

- Array methods are your best friends
- Spread operator (`...`) helps with immutability
- Arrow functions make functional code more concise
- Consider using `const` by default to prevent reassignment

## Next Steps

1. **Practice with array methods**: Master map, filter, reduce, find, some, every
2. **Learn a functional library**: Try Ramda or Lodash/FP for JavaScript
3. **Study recursion**: Many functional solutions use recursion instead of loops
4. **Explore functional languages**: Consider learning Elm, Clojure, or Haskell to deepen understanding

---

Remember: Functional programming is a mindset shift. Start by applying one or two concepts at a time, and gradually you'll develop the intuition for thinking functionally.

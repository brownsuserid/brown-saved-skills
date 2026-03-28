# React Anti-Patterns Catalog

This reference covers React component and state management anti-patterns.

## State Management Anti-Patterns

### Storing Derived State

**What:** Storing computed values in state instead of deriving them.

**Why Bad:** Extra state to maintain, potential for inconsistency, unnecessary re-renders.

```jsx
// Bad: Derived state stored
function ProductList({ products }) {
  const [items, setItems] = useState(products);
  const [filteredItems, setFilteredItems] = useState(products);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    setFilteredItems(items.filter(i => i.name.includes(searchTerm)));
  }, [items, searchTerm]);

  return <List items={filteredItems} />;
}

// Good: Compute during render
function ProductList({ products }) {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredItems = products.filter(i =>
    i.name.includes(searchTerm)
  );

  return <List items={filteredItems} />;
}
```

### Direct State Mutation

**What:** Modifying state objects directly instead of creating new ones.

**Why Bad:** React won't detect changes, component won't re-render.

```jsx
// Bad: Direct mutation
function handleAdd(item) {
  items.push(item);  // Mutates existing array
  setItems(items);   // Same reference, no re-render
}

// Good: Create new array
function handleAdd(item) {
  setItems([...items, item]);
}

// Bad: Object mutation
user.name = 'New Name';
setUser(user);

// Good: New object
setUser({ ...user, name: 'New Name' });
```

### State as Regular Variable

**What:** Declaring state as a regular variable, not using hooks.

**Why Bad:** Variable resets on every render, no persistence.

```jsx
// Bad: Regular variable
function Counter() {
  let count = 0;  // Resets every render!

  return <button onClick={() => count++}>{count}</button>;
}

// Good: useState
function Counter() {
  const [count, setCount] = useState(0);

  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}
```

### Missing Hook Dependencies

**What:** Omitting dependencies from useEffect/useCallback/useMemo.

**Why Bad:** Stale closures, bugs that are hard to trace.

```jsx
// Bad: Missing dependency
function Search({ query }) {
  const [results, setResults] = useState([]);

  useEffect(() => {
    fetchResults(query).then(setResults);
  }, []);  // Missing 'query'!

  return <Results items={results} />;
}

// Good: All dependencies listed
useEffect(() => {
  fetchResults(query).then(setResults);
}, [query]);
```

## Component Anti-Patterns

### Props Drilling

**What:** Passing props through many intermediate components.

**Why Bad:** Components become coupled, changes require updating many files.

```jsx
// Bad: Props drilling
function App() {
  const [user, setUser] = useState(null);
  return <Layout user={user} setUser={setUser} />;
}

function Layout({ user, setUser }) {
  return <Sidebar user={user} setUser={setUser} />;
}

function Sidebar({ user, setUser }) {
  return <UserMenu user={user} setUser={setUser} />;
}

// Good: Context
const UserContext = createContext();

function App() {
  const [user, setUser] = useState(null);
  return (
    <UserContext.Provider value={{ user, setUser }}>
      <Layout />
    </UserContext.Provider>
  );
}

function UserMenu() {
  const { user, setUser } = useContext(UserContext);
  return <div>{user.name}</div>;
}
```

### Using Array Index as Key

**What:** Using `index` as the `key` prop in lists.

**Why Bad:** Causes incorrect re-renders when list order changes.

```jsx
// Bad: Index as key
{items.map((item, index) => (
  <ListItem key={index} item={item} />
))}

// Good: Stable unique ID
{items.map(item => (
  <ListItem key={item.id} item={item} />
))}
```

### Inline Object/Array Props

**What:** Creating new objects/arrays inline in JSX.

**Why Bad:** Creates new reference every render, breaks memoization.

```jsx
// Bad: New object every render
<Component style={{ color: 'red' }} />
<Component items={[1, 2, 3]} />
<Component config={{ timeout: 1000 }} />

// Good: Define outside or memoize
const style = { color: 'red' };
const items = [1, 2, 3];

function Parent() {
  const config = useMemo(() => ({ timeout: 1000 }), []);

  return <Component style={style} items={items} config={config} />;
}
```

### Giant Components

**What:** Components with 500+ lines doing too much.

**Fix:** Split into smaller, focused components.

```jsx
// Bad: Giant component
function Dashboard() {
  // 500+ lines of state, effects, handlers, JSX
  return (
    <div>
      {/* Header section - 100 lines */}
      {/* Sidebar section - 150 lines */}
      {/* Main content - 200 lines */}
      {/* Footer - 50 lines */}
    </div>
  );
}

// Good: Composed of smaller components
function Dashboard() {
  return (
    <DashboardLayout>
      <DashboardHeader />
      <DashboardSidebar />
      <DashboardContent />
      <DashboardFooter />
    </DashboardLayout>
  );
}
```

## Hook Anti-Patterns

### useEffect for Synchronous Computation

**What:** Using useEffect for calculations that can happen during render.

**Why Bad:** Extra render cycle, potential for flicker.

```jsx
// Bad: Effect for sync computation
function ProductPrice({ price, discount }) {
  const [finalPrice, setFinalPrice] = useState(0);

  useEffect(() => {
    setFinalPrice(price * (1 - discount));
  }, [price, discount]);

  return <span>{finalPrice}</span>;  // Flickers!
}

// Good: Compute during render
function ProductPrice({ price, discount }) {
  const finalPrice = price * (1 - discount);
  return <span>{finalPrice}</span>;
}
```

### Using useRef for Mutable State That Affects Render

**What:** Using useRef when useState is needed.

**Why Bad:** Changes don't trigger re-renders.

```jsx
// Bad: useRef for render-affecting state
function Counter() {
  const count = useRef(0);

  return (
    <button onClick={() => count.current++}>
      {count.current}  {/* Never updates! */}
    </button>
  );
}

// useRef is correct for: DOM refs, interval IDs, previous values
```

### Creating Components Inside Components

**What:** Defining components inside other components.

**Why Bad:** New component instance every render, loses state.

```jsx
// Bad: Component inside component
function Parent({ items }) {
  // New ListItem definition every render!
  function ListItem({ item }) {
    const [selected, setSelected] = useState(false);
    return <div>{item.name}</div>;
  }

  return items.map(item => <ListItem key={item.id} item={item} />);
}

// Good: Define outside
function ListItem({ item }) {
  const [selected, setSelected] = useState(false);
  return <div>{item.name}</div>;
}

function Parent({ items }) {
  return items.map(item => <ListItem key={item.id} item={item} />);
}
```

## Performance Anti-Patterns

### Everything in Single Context

**What:** One giant context for all app state.

**Why Bad:** Any change re-renders all consumers.

```jsx
// Bad: Monolithic context
const AppContext = createContext();

function App() {
  const [user, setUser] = useState(null);
  const [theme, setTheme] = useState('light');
  const [cart, setCart] = useState([]);
  const [notifications, setNotifications] = useState([]);

  return (
    <AppContext.Provider value={{ user, theme, cart, notifications, ... }}>
      <MainApp />
    </AppContext.Provider>
  );
}

// Good: Split by concern
<UserProvider>
  <ThemeProvider>
    <CartProvider>
      <MainApp />
    </CartProvider>
  </ThemeProvider>
</UserProvider>
```

### Premature useMemo/useCallback

**What:** Memoizing everything "just in case".

**Why Bad:** Memoization has overhead, often not needed.

```jsx
// Bad: Over-memoization
function Component({ name }) {
  const greeting = useMemo(() => `Hello, ${name}`, [name]);  // Overkill
  const handleClick = useCallback(() => console.log('clicked'), []);

  return <div onClick={handleClick}>{greeting}</div>;
}

// Good: Memoize when needed
// - Expensive calculations
// - Props to memoized children
// - Dependencies of other hooks
```

### Rendering Large Lists Without Virtualization

**What:** Rendering thousands of items at once.

**Why Bad:** Slow initial render, high memory usage.

```jsx
// Bad: Render all items
function ProductList({ products }) {
  return (
    <ul>
      {products.map(p => <ProductItem key={p.id} product={p} />)}
    </ul>
  );  // 10,000 items = pain
}

// Good: Use virtualization
import { FixedSizeList } from 'react-window';

function ProductList({ products }) {
  return (
    <FixedSizeList
      height={600}
      itemCount={products.length}
      itemSize={50}
    >
      {({ index, style }) => (
        <ProductItem style={style} product={products[index]} />
      )}
    </FixedSizeList>
  );
}
```

## Detection Commands

```bash
# Find large components
find . -name "*.tsx" -o -name "*.jsx" | xargs wc -l | sort -rn | head -20

# Find index as key
rg "key=\{.*index" -g "*.tsx" -g "*.jsx"

# Find inline objects in props
rg "=\{\{" -g "*.tsx" -g "*.jsx"

# Find potential props drilling
rg "props\." -g "*.tsx" -c | sort -t: -k2 -rn | head -10

# Find missing dependencies (ESLint)
npx eslint --rule 'react-hooks/exhaustive-deps: error' .
```

## References

- [React Anti-Patterns and Best Practices](https://www.perssondennis.com/articles/react-anti-patterns-and-best-practices-dos-and-donts)
- [6 Common React Anti-Patterns](https://itnext.io/6-common-react-anti-patterns-that-are-hurting-your-code-quality-904b9c32e933)
- [15 React Anti-Patterns](https://jsdev.space/react-anti-patterns-2025/)
- [React Performance Anti-Patterns](https://dev.to/myogeshchavan97/react-performance-anti-patterns-5-mistakes-that-kill-your-apps-speed-76j)

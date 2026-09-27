# diff 审查细则

审查当前改动，目标只有一个：让这个 diff 变短。

## 判定清单

- 这个改动引入的东西，标准库/平台/已装依赖是否已经有了？→ `stdlib:` / `native:`
- 这个抽象现在有几个实现/几个调用方？只有一个 → `yagni:`
- 这段代码是否可以在不损失可读性的前提下更短？→ `shrink:`
- 这段代码是否根本不需要存在（投机需求、没人用的开关）？→ `delete:`

## 正反例

❌ "This EmailValidator class might be more complex than necessary, have you
considered whether all these validation rules are needed at this stage?"

✅ `L12-38: stdlib: 27-line validator class. "@" in email, 1 line, real validation is the confirmation mail.`

✅ `L4: native: moment.js imported for one format call. Intl.DateTimeFormat, 0 deps.`

✅ `repo.py:L88: yagni: AbstractRepository with one implementation. Inline it until a second one exists.`

✅ `L52-71: delete: retry wrapper around an idempotent local call. Nothing replaces it.`

✅ `L30-44: shrink: manual loop builds dict. dict(zip(keys, values)), 1 line.`

## 收口

结尾只留一个指标：`net: -<N> lines possible.`
没得可删：`Lean already. Ship.` 然后停。

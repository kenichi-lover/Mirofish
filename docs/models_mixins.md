## sa_column 的作用与用途
在 SQLModel 中，Field() 已经封装了大部分常用的数据库列属性（如 primary_key、index、nullable 等）。
然而，当你需要使用一些更高级或原生的 SQLAlchemy 特性（而 SQLModel 的 Field 没有直接提供对应参数）时，
就可以通过 sa_column 传入一个原生的 SQLAlchemy Column 对象。

## 常见的使用场景包括：
使用复杂的原生 SQLAlchemy 数据类型或自定义类型。
设置高级约束（如复合唯一约束、复杂的检查约束 CheckConstraint）。
使用数据库层面的服务器默认值 (server_default)。




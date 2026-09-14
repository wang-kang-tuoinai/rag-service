Go 语言支持C风格的块注释 `/* */` 和C++风格的行注释 `//`。 行注释更为常用，而块注释则主要用作包的注释，当然也可在禁用一大段代码时使用。

`godoc` 既是一个程序，又是一个 Web 服务器，它对 Go 的源码进行处理，并提取包中的文档内容。 出现在顶级声明之前，且与该声明之间没有空行的注释，将与该声明一起被提取出来，作为该条目的说明文档。 这些注释的类型和风格决定了 `godoc` 生成的文档质量。

每个包都应包含一段**包注释**，即放置在包子句前的一个块注释。对于包含多个文件的包， 包注释只需出现在其中的任一文件中即可。包注释应在整体上对该包进行介绍，并提供包的相关信息。 它将出现在 `godoc` 页面中的最上面，并为紧随其后的内容建立详细的文档。

```
/*
regexp 包为正则表达式实现了一个简单的库。

该库接受的正则表达式语法为：

    regexp:
        concatenation { '|' concatenation }
    concatenation:
        { closure }
    closure:
        term [ '*' | '+' | '?' ]
    term:
        '^'
        '$'
        '.'
        character
        '[' [ '^' ] character-ranges ']'
        '(' regexp ')'
*/
package regexp

```

若某个包比较简单，包注释同样可以简洁些。

```
// path 包实现了一些常用的工具，
// 以便于操作用反斜杠分隔的路径.
```

注释无需进行额外的格式化，如用星号来突出等。生成的输出甚至可能无法以等宽字体显示， 因此不要依赖于空格对齐，`godoc` 会像 `gofmt` 那样处理好这一切。 注释是不会被解析的纯文本，因此像HTML或其它类似于 `_这样_` 的东西将按照 **原样** 输出，因此不应使用它们。`godoc` 所做的调整， 就是将已缩进的文本以等宽字体显示，来适应对应的程序片段。 [`fmt` 包](http://golang.org/pkg/fmt/)的注释就用了这种不错的效果。

`godoc` 是否会重新格式化注释取决于上下文，因此必须确保它们看起来清晰易辨： 使用正确的拼写、标点和语句结构以及折叠长行等。

在包中，任何顶级声明前面的注释都将作为该声明的**文档注释**。 在程序中，每个可导出（首字母大写）的名称都应该有文档注释。

文档注释最好是完整的句子，这样它才能适应各种自动化的展示。 第一句应当以被声明的东西开头，并且是单句的摘要。

```
// Compile 用于解析正则表达式并返回，如果成
// 功，则 Regexp 对象就可用于匹配所针对的文本。
func Compile(str string) (*Regexp, error) {
```

若注释总是以名称开头，`go doc` 命令的输出就能通过 `grep` 变得更加有用。假如你记不住 `Compile` 这个名称，而又在找正则表达式的解析函数（『解析』意味着关键词为 `parse`）， 那就可以运行

```
$ go doc -all regexp | grep -i parse
```

若包中的所有文档注释都以 `This function...` 开头，`grep` 就无法帮你回想起此名称。 但由于每个包的文档注释都以其名称开头，你就能看到这样的内容，它能显示你正在寻找的词语。

```
$ go doc -all regexp | grep -i parse
    Compile parses a regular expression and returns, if successful, a Regexp
    MustCompile is like Compile but panics if the expression cannot be parsed.
    parsed. It simplifies safe initialization of global variables holding
$

```

Go的声明语法允许成组声明。单个文档注释应介绍一组相关的常量或变量。 由于是整体声明，这种注释往往较为笼统。


```
// 表达式解析失败后返回错误代码
var (
    ErrInternal      = errors.New("regexp: internal error")
    ErrUnmatchedLpar = errors.New("regexp: unmatched '('")
    ErrUnmatchedRpar = errors.New("regexp: unmatched ')'")
    ...
)

```

即便是对于私有名称，也可通过成组声明来表明各项间的关系，例如某一组由互斥体保护的变量。

```
var (
    countLock   sync.Mutex
    inputCount  uint32
    outputCount uint32
    errorCount  uint32
)
```
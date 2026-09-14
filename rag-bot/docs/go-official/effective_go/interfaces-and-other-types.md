### 接口

Go中的接口为指定对象的行为提供了一种方法：如果某样东西可以完成**这个**， 那么它就可以用在**这里**。我们已经见过许多简单的示例了；通过实现 `String` 方法，我们可以自定义打印函数，而通过 `Write` 方法，`Fprintf` 则能对任何对象产生输出。在Go代码中， 仅包含一两种方法的接口很常见，且其名称通常来自于实现它的方法， 如 `io.Writer` 就是实现了 `Write` 的一类对象。

每种类型都能实现多个接口。例如一个实现了 `sort.Interface` 接口的集合就可通过 `sort` 包中的例程进行排序。该接口包括 `Len()`、`Less(i, j int) bool` 以及 `Swap(i, j int)`，另外，该集合仍然可以有一个自定义的格式化器。 以下特意构建的例子 `Sequence` 就同时满足这两种情况。

```
type Sequence []int

// sort.Interface所需的方法。
func (s Sequence) Len() int {
    return len(s)
}
func (s Sequence) Less(i, j int) bool {
    return s[i] < s[j]
}
func (s Sequence) Swap(i, j int) {
    s[i], s[j] = s[j], s[i]
}

// Copy方法返回Sequence的复制
func (s Sequence) Copy() Sequence {
    copy := make(Sequence, 0, len(s))
    return append(copy, s...)
}

// 打印方法-在打印前给元素排序
func (s Sequence) String() string {
    s = s.Copy() // 复制s，不要覆盖参数本身
    sort.Sort(s)
    str := "["
    for i, elem := range s { // Loop空间复杂度是O(N²)；将在下个例子中修复它
        if i > 0 {
            str += " "
        }
        str += fmt.Sprint(elem)
    }
    return str + "]"
}
```



### 类型转换

`Sequence` 的 `String` 方法重新实现了 `Sprint` 为切片实现的功能。若我们在调用 `Sprint` 之前将 `Sequence` 转换为纯粹的 `[]int`，就能共享已实现的功能。

```
func (s Sequence) String() string {
    s = s.Copy()
    sort.Sort(s)
    return fmt.Sprint([]int(s))
}

```

该方法是通过类型转换技术，在 `String` 方法中安全调用 `Sprintf` 的另个一例子。若我们忽略类型名的话，这两种类型（`Sequence`和 `[]int`）其实是相同的，因此在二者之间进行转换是合法的。 转换过程并不会创建新值，它只是暂时让现有的值看起来有个新类型而已。 （还有些合法转换则会创建新值，如从整数转换为浮点数等。）

在Go程序中，为访问不同的方法集而进行类型转换的情况非常常见。 例如，我们可使用现有的 `sort.IntSlice` 类型来简化整个示例：

```
type Sequence []int

// 打印方法-在打印之前对元素进行排序
func (s Sequence) String() string {
    s = s.Copy()
    sort.IntSlice(s).Sort()
    return fmt.Sprint([]int(s))
}

```

现在，不必让 `Sequence` 实现多个接口（排序和打印）， 我们可通过将数据条目转换为多种类型（`Sequence`、`sort.IntSlice` 和 `[]int`）来使用相应的功能，每次转换都完成一部分工作。 这在实践中虽然有些不同寻常，但往往却很有效。

### 接口转换与类型断言

[类型选择](https://learnku.com/docs/effective-go/2020/control-structure/6241#bca1f2) 是类型转换的一种形式：它接受一个接口，在选择 （switch）中根据其判断选择对应的情况（case）， 并在某种意义上将其转换为该种类型。以下代码为 `fmt.Printf` 通过类型选择将值转换为字符串的简化版。若它已经为字符串，我们需要该接口中实际的字符串值； 若它有 String 方法，我们则需要调用该方法所得的结果。

```
type Stringer interface {
    String() string
}

var value interface{} // Value 由调用者提供
switch str := value.(type) {
case string:
    return str
case Stringer:
    return str.String()
}

```

第一种情况获取具体的值，第二种将该接口转换为另一个接口。这种方式对于混合类型来说非常完美。

若我们只关心一种类型呢？若我们知道该值拥有一个 `string` 而想要提取它呢？ 只需一种情况的类型选择就行，但它需要**类型断言**。类型断言接受一个接口值， 并从中提取指定的明确类型的值。其语法借鉴自类型选择开头的子句，但它需要一个明确的类型， 而非 `type` 关键字：

```
value.(typeName)

```


而其结果则是拥有静态类型 `typeName` 的新值。该类型必须为该接口所拥有的具体类型， 或者该值可转换成的第二种接口类型。要提取我们知道在该值中的字符串，可以这样：

```
str := value.(string)

```


但若它所转换的值中不包含字符串，该程序就会以运行时错误崩溃。为避免这种情况， 需使用“逗号, ok”惯用测试它能安全地判断该值是否为字符串：

```
str, ok := value.(string)
if ok {
    fmt.Printf("string value is: %q\n", str)
} else {
    fmt.Printf("value is not a string\n")
}

```

若类型断言失败，str 将继续存在且为字符串类型，但它将拥有零值，即空字符串。

作为对能量的说明，这里有个 if-else 语句，它等价于本节开头的类型选择。

```
if str, ok := value.(string); ok {
    return str
} else if str, ok := value.(Stringer); ok {
    return str.String()
}

```



### 通用性

若某种现有的类型仅实现了一个接口，且除此之外并无可导出的方法，则该类型本身就无需导出。 仅导出该接口能让我们更专注于其行为而非实现，其它属性不同的实现则能镜像该原始类型的行为。 这也能够避免为每个通用接口的实例重复编写文档。

在这种情况下，构造函数应当返回一个接口值而非实现的类型。例如在 `hash` 库中，`crc32.NewIEEE` 和 `adler32.New` 都返回接口类型 `hash.Hash32`。要在Go程序中用Adler-32算法替代CRC-32， 只需修改构造函数调用即可，其余代码则不受算法改变的影响。

同样的方式能将 `crypto` 包中多种联系在一起的流密码算法与块密码算法分开。 `crypto/cipher` 包中的 `Block` 接口指定了块密码算法的行为， 它为单独的数据块提供加密。接着，和 `bufio` 包类似，任何实现了该接口的密码包都能被用于构造以 `Stream` 为接口表示的流密码，而无需知道块加密的细节。

`crypto/cipher` 接口看其来就像这样：

```
type Block interface {
    BlockSize() int
    Encrypt(dst, src []byte)
    Decrypt(dst, src []byte)
}

type Stream interface {
    XORKeyStream(dst, src []byte)
}

```

这是计数器模式CTR流的定义，它将块加密改为流加密，注意块加密的细节已被抽象化了。

```
// NewCTR 返回使用中给定的块加密/解密的流
// 计数器模式。iv 的长度必须与块的块大小相同
func NewCTR(block Block, iv []byte) Stream

```

`NewCTR` 的应用并不仅限于特定的加密算法和数据源，它适用于任何对 `Block` 接口和 `Stream` 的实现。因为它们返回接口值， 所以用其它加密模式来代替CTR只需做局部的更改。构造函数的调用过程必须被修改， 但由于其周围的代码只能将它看做 `Stream`，因此它们不会注意到其中的区别。

### 接口和方法

由于几乎任何类型都能添加方法，因此几乎任何类型都能满足一个接口。一个很直观的例子就是 `http` 包中定义的 `Handler` 接口。任何实现了 `Handler` 的对象都能够处理HTTP请求。

```
type Handler interface {
    ServeHTTP(ResponseWriter, *Request)
}

```

`ResponseWriter` 接口提供了对方法的访问，这些方法需要响应客户端的请求。 由于这些方法包含了标准的 `Write` 方法，因此 `http.ResponseWriter` 可用于任何 `io.Writer` 适用的场景。`Request` 结构体包含已解析的客户端请求。

为简单起见，我们假设所有的 HTTP 请求都是GET方法，而忽略POST方法， 这种简化不会影响处理程序的建立方式。这里有个短小却完整的处理程序实现， 它用于记录某个页面被访问的次数。

```
// 简单的计数器服务器。
type Counter struct {
    n int
}

func (ctr *Counter) ServeHTTP(w http.ResponseWriter, req *http.Request) {
    ctr.n++
    fmt.Fprintf(w, "counter = %d\n", ctr.n)
}

```

（紧跟我们的主题，注意 Fprintf 如何能输出到 http.ResponseWriter。） 作为参考，这里演示了如何将这样一个服务器添加到URL树的一个节点上。

```
import "net/http"
...
ctr := new(Counter)
http.Handle("/counter", ctr)

```

但为什么 `Counter` 要是结构体呢？一个整数就够了。（接收者必须为指针，增量操作对于调用者才可见。）

```
// 简单的计数器服务。
type Counter int

func (ctr *Counter) ServeHTTP(w http.ResponseWriter, req *http.Request) {
    *ctr++
    fmt.Fprintf(w, "counter = %d\n", *ctr)
}

```

当页面被访问时，怎样通知你的程序去更新一些内部状态呢？为Web页面绑定个信道吧。

```
// 每次浏览该信道都会发送一个提醒。
// （可能需要带缓冲的信道。）
type Chan chan *http.Request

func (ch Chan) ServeHTTP(w http.ResponseWriter, req *http.Request) {
    ch <- req
    fmt.Fprint(w, "notification sent")
}

```



最后，假设我们需要输出调用服务器二进制程序时使用的实参 `/args`。 很简单，写个打印实参的函数就行了。

```
func ArgServer() {
    fmt.Println(os.Args)
}

```

我们如何将它转换为HTTP服务器呢？我们可以将 `ArgServer` 实现为某种可忽略值的方法，不过还有种更简单的方法。 既然我们可以为除指针和接口以外的任何类型定义方法，同样也能为一个函数写一个方法。 `http` 包包含以下代码：

```
// HandlerFunc 类型是一个适配器，
// 它允许将普通函数用做HTTP处理程序。
// 若 f 是个具有适当签名的函数，
// HandlerFunc(f) 就是个调用 f 的处理程序对象。
type HandlerFunc func(ResponseWriter, *Request)

// ServeHTTP calls f(w, req).
func (f HandlerFunc) ServeHTTP(w ResponseWriter, req *Request) {
    f(w, req)
}

```

`HandlerFunc` 是个具有 `ServeHTTP` 方法的类型， 因此该类型的值就能处理HTTP请求。我们来看看该方法的实现：接收者是一个函数 `f`，而该方法调用 `f`。这看起来很奇怪，但不必大惊小怪， 区别在于接收者变成了一个信道，而方法通过该信道发送消息。

为了将 `ArgServer` 实现成HTTP服务器，首先我们得让它拥有合适的签名。

```
// 实参服务器。
func ArgServer(w http.ResponseWriter, req *http.Request) {
    fmt.Fprintln(w, os.Args)
}

```

`ArgServer` 和 `HandlerFunc` 现在拥有了相同的签名， 因此我们可将其转换为这种类型以访问它的方法，就像我们将 `Sequence` 转换为 `IntSlice` 以访问 `IntSlice.Sort` 那样。 建立代码非常简单：

```
http.Handle("/args", http.HandlerFunc(ArgServer))

```


当有人访问 `/args` 页面时，安装到该页面的处理程序就有了值 `ArgServer` 和类型 `HandlerFunc`。 HTTP服务器会以 `ArgServer` 为接收者，调用该类型的 `ServeHTTP` 方法，它会反过来调用 `ArgServer`（通过 `f(c, req)`），接着实参就会被显示出来。

在本节中，我们通过一个结构体，一个整数，一个信道和一个函数，建立了一个HTTP服务器， 这一切都是因为接口只是方法的集合，而几乎任何类型都能定义方法。
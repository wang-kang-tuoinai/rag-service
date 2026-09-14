### 通过通信共享内存

并发编程是个很大的论题。但限于篇幅，这里仅讨论一些Go特有的东西。

在并发编程中，为实现对共享变量的正确访问需要精确的控制，这在多数环境下都很困难。 Go语言另辟蹊径，它将共享的值通过信道传递，实际上，多个独立执行的线程从不会主动共享。 在任意给定的时间点，只有一个Go协程能够访问该值。数据竞争从设计上就被杜绝了。 为了提倡这种思考方式，我们将它简化为一句口号：

> 不要通过共享内存来通信，而应通过通信来共享内存。

这种方法意义深远。例如，引用计数通过为整数变量添加互斥锁来很好地实现。 但作为一种高级方法，通过信道来控制访问能够让你写出更简洁，正确的程序。

我们可以从典型的单线程运行在单CPU之上的情形来审视这种模型。它无需提供同步原语。 现在考虑另一种情况，它也无需同步。现在让它们俩进行通信。若将通信过程看作同步， 那就完全不需要其它同步了。例如，Unix管道就与这种模型完美契合。 尽管Go的并发处理方式来源于Hoare的通信顺序处理（CSP）， 它依然可以看作是类型安全的Unix管道的实现。


### 协程（goroutine）

我们称之为**Go 协程**是因为现有的术语—线程、协程、进程等等—无法准确传达它的含义。 Go 协程具有简单的模型：它是与其它Go 协程并发运行在同一地址空间的函数。它是轻量级的， 所有消耗几乎就只有栈空间的分配。而且栈最开始是非常小的，所以它们很廉价， 仅在需要时才会随着堆空间的分配（和释放）而变化。

Go 协程在多线程操作系统上可实现多路复用，因此若一个线程阻塞，比如说等待I/O， 那么其它的线程就会运行。Go 协程的设计隐藏了线程创建和管理的诸多复杂性。

在函数或方法前添加 `go` 关键字能够在新的Go 协程中调用它。当调用完成后， 该Go 协程也会安静地退出。（效果有点像Unix Shell中的 `&` 符号，它能让命令在后台运行。）


```
go list.Sort()  // 同时运行 list.Sort ; 不需要等待

```

匿名函数在协程中调用非常方便：

```
func Announce(message string, delay time.Duration) {
    go func() {
        time.Sleep(delay)
        fmt.Println(message)
    }()  // 注意括号 - 必须调用函数
}

```

在Go中，匿名函数都是闭包：其实现在保证了函数内引用变量的生命周期与函数的活动时间相同。

这些函数没什么实用性，因为它们没有实现完成时的信号处理。因此，我们需要信道。

### 信道

信道与映射一样，也需要通过 `make` 来分配内存。其结果值充当了对底层数据结构的引用。 若提供了一个可选的整数形参，它就会为该信道设置缓冲区大小。默认值是零，表示不带缓冲的或同步的信道。

```
ci := make(chan int)            // 整数无缓冲信道
cj := make(chan int, 0)         // 整数无缓冲信道
cs := make(chan *os.File, 100)  // 指向文件的指针的缓冲信道

```

无缓冲信道在通信时会同步交换数据，它能确保（两个Go协程的）计算处于确定状态。

信道有很多惯用法，我们从这里开始了解。在上一节中，我们在后台启动了排序操作。 信道使得启动的Go协程等待排序完成。

```
c := make(chan int)  // 创建一个无缓冲的类型为整型的 channel 。
//用 goroutine 开始排序；当它完成时，会在信道上发信号。
go func() {
    list.Sort()
    c <- 1  // 发送一个信号，这个值并没有具体意义
}()
doSomethingForAWhile()
<-c   // 等待 sort 执行完成，然后从 channel 取值

```

接收者在收到数据前会一直阻塞。若信道是不带缓冲的，那么在接收者收到值前， 发送者会一直阻塞；若信道是带缓冲的，则发送者仅在值被复制到缓冲区前阻塞； 若缓冲区已满，发送者会一直等待直到某个接收者取出一个值为止。

带缓冲的信道可被用作信号量，例如限制吞吐量。在此例中，进入的请求会被传递给 `handle`，它向信道内发送一个值，处理请求后将值从信道中取回，以便让该 “信号量”准备迎接下一次请求。信道缓冲区的容量决定了同时调用 `process` 的数量上限，因此我们在初始化时首先要填充至它的容量上限。

```
var sem = make(chan int, MaxOutstanding)

func handle(r *Request) {
    sem <- 1    // 等待活动队列清空。
    process(r)  // 可能需要很长时间。
    <-sem       // 完成；使下一个请求可以运行。
}

func Serve(queue chan *Request) {
    for {
        req := <-queue
        go handle(req)  // 无需等待 handle 结束。
    }
}

```

一旦有`MaxOutstanding`个处理程序正在执行 `process`，缓冲区已满的信道的操作都暂停接收更多操作，直到至少一个程序完成并从缓冲区接收。

然而，它却有个设计问题：尽管只有 `MaxOutstanding` 个Go协程能同时运行，但 `Serve` 还是为每个进入的请求都创建了新的Go协程。其结果就是，若请求来得很快， 该程序就会无限地消耗资源。为了弥补这种不足，我们可以通过修改 `Serve` 来限制创建Go协程，这是个明显的解决方案，但要当心我们修复后出现的Bug。

```
func Serve(queue chan *Request) {
    for req := range queue {
        sem <- 1
        go func() {
            process(req) // Buggy; see explanation below.
            <-sem
        }()
    }
}
```

Bug出现在Go的 `for` 循环中，该循环变量在每次迭代时会被重用，因此 `req` 变量会在所有的Go协程间共享，这不是我们想要的。我们需要确保 `req` 对于每个Go协程来说都是唯一的。有一种方法能够做到，就是将 `req` 的值作为实参传入到该Go协程的闭包中：

```
func Serve(queue chan *Request) {
    for req := range queue {
        sem <- 1
        go func(req *Request) {
            process(req)
            <-sem
        }(req)
    }
}
```



比较前后两个版本，观察该闭包声明和运行中的差别。 另一种解决方案就是以相同的名字创建新的变量，如例中所示：

```
func Serve(queue chan *Request) {
    for req := range queue {
        req := req // 为该Go协程创建 req 的新实例。
        sem <- 1
        go func() {
            process(req)
            <-sem
        }()
    }
}
```

它的写法看起来有点奇怪

```
req := req

```


但在 Go 中这样做是合法且常见的。你用相同的名字获得了该变量的一个新的版本， 以此来局部地刻意屏蔽循环变量，使它对每个 Go 协程保持唯一。


回到编写服务器的一般问题上来。另一种管理资源的好方法就是启动固定数量的 `handle` Go协程，一起从请求信道中读取数据。Go协程的数量限制了同时调用 `process` 的数量。`Serve` 同样会接收一个通知退出的信道， 在启动所有Go协程后，它将阻塞并暂停从信道中接收消息。

```
func handle(queue chan *Request) {
    for r := range queue {
        process(r)
    }
}

func Serve(clientRequests chan *Request, quit chan bool) {
    // 启动处理程序
    for i := 0; i < MaxOutstanding; i++ {
        go handle(clientRequests)
    }
    <-quit  // 等待通知退出。
}

```

### 信道中的信道

Go最重要的特性就是信道是一等值，它可以被分配并像其它值到处传递。 这种特性通常被用来实现安全、并行的多路分解。

在上一节的例子中，`handle` 是个非常理想化的请求处理程序， 但我们并未定义它所处理的请求类型。若该类型包含一个可用于回复的信道， 那么每一个客户端都能为其回应提供自己的路径。以下为 `Request` 类型的大概定义。


```
type Request struct {
    args        []int
    f           func([]int) int
    resultChan  chan int
}

```

客户端提供了一个函数及其实参，此外在请求对象中还有个接收应答的信道。

```
func sum(a []int) (s int) {
    for _, v := range a {
        s += v
    }
    return
}

request := &Request{[]int{3, 4, 5}, sum, make(chan int)}
// 发送请求
clientRequests <- request
// 等待回应
fmt.Printf("answer: %d\n", <-request.resultChan)

```


服务端我们只修改 `handler` 函数：

```
func handle(queue chan *Request) {
    for req := range queue {
        req.resultChan <- req.f(req.args)
    }
}

```

要使其实际可用还有很多工作要做，这些代码仅能实现一个速率有限、并行、非阻塞RPC系统的 框架，而且它并不包含互斥锁。



### 并行化

这些设计的另一个应用是在多CPU核心上实现并行计算。如果计算过程能够被分为几块 可独立执行的过程，它就可以在每块计算结束时向信道发送信号，从而实现并行处理。

让我们看看这个理想化的例子。我们在对一系列向量项进行极耗资源的操作， 而每个项的值计算是完全独立的。


```
type Vector []float64

// 将此操应用至 v[i], v[i+1] ... 直到 v[n-1]
func (v Vector) DoSome(i, n int, u Vector, c chan int) {
    for ; i < n; i++ {
        v[i] += u.Op(v[i])
    }
    c <- 1    // signal that this piece is done
}

```

我们在循环中启动了独立的处理块，每个CPU将执行一个处理。 它们有可能以乱序的形式完成并结束，但这没有关系； 我们只需在所有Go协程开始后接收，并统计信道中的完成信号即可。

```
const numCPU = 4 // CPU 核心数

func (v Vector) DoAll(u Vector) {
    c := make(chan int, numCPU)  // 缓冲区是可选的，但明显用上更好
    for i := 0; i < numCPU; i++ {
        go v.DoSome(i*len(v)/numCPU, (i+1)*len(v)/numCPU, u, c)
    }
    // 排空信道。
    for i := 0; i < numCPU; i++ {
        <-c    // 等待任务完成
    }
    // 一切完成
}

```

除了直接设置 `numCPU` 常量值以外，我们还可以向 runtime 询问一个合理的值。函数  `[runtime.NumCPU](https://golang.org/pkg/runtime#NumCPU)` 可以返回硬件 CPU 上的核心数量，如此使用：

```
var numCPU = runtime.NumCPU()

```



另外一个需要知道的函数是 [`runtime.GOMAXPROCS`](https://golang.org/pkg/runtime#GOMAXPROCS)，设置当前最大可用的CPU 数量，返回的是之前设置的最大可用的CPU数量。默认情况下使用  `runtime.NumCPU`的值，但是可以被命令行环境变量，或者调用此函数并传参正整数。传参 0 的话会返回值，假如说我们尊重用户对资源的分配，就应该这么写：

```
var numCPU = runtime.GOMAXPROCS(0)

```

注意不要混淆并发（concurrency）和并行（parallelism）的概念：并发是用可独立执行组件构造程序的方法， 而并行则是为了效率在多 CPU 上平行地进行计算。尽管 Go 的并发特性能够让某些问题更易构造成并行计算， 但 Go 仍然是种并发而非并行的语言，且 Go 的模型并不适合所有的并行问题。 关于其中区别的讨论，见 [此博文](http://blog.golang.org/2013/01/concurrency-is-not-parallelism.html)。


### 漏桶缓存区限流设计

并发编程的工具甚至能很容易地表达非并发的思想。这里有个提取自 RPC 包的例子。 客户端 Go 协程从某些来源，可能是网络中循环接收数据。为避免分配和释放缓冲区， 它保存了一个空闲链表，使用一个带缓冲信道表示。若信道为空，就会分配新的缓冲区。 一旦消息缓冲区就绪，它将通过 `serverChan` 被发送到服务器。

```
var freeList = make(chan *Buffer, 100)
var serverChan = make(chan *Buffer)

func client() {
    for {
        var b *Buffer
        // 若缓冲区可用就用它，不可用就分配个新的。
        select {
        case b = <-freeList:
            // 获取一个，不做别的。
        default:
            // 非空闲，因此分配一个新的。
            b = new(Buffer)
        }
        load(b)              // 从网络中读取下一条消息。
        serverChan <- b      // 发送至服务器。
    }
}

```

服务器从客户端循环接收每个消息，处理它们，并将缓冲区返回给空闲列表。

```
func server() {
    for {
        b := <-serverChan    // 等待工作。
        process(b)
        // 若缓冲区有空间就重用它。
        select {
        case freeList <- b:
            // 将缓冲区放到空闲列表中，不做别的。
        default:
            // 空闲列表已满，保持就好。
        }
    }
}

```

客户端试图从 `freeList` 中获取缓冲区；若没有缓冲区可用， 它就将分配一个新的。服务器将 `b` 放回空闲列表 `freeList` 中直到列表已满，此时缓冲区将被丢弃，并被垃圾回收器回收。（`select` 语句中的 `default` 子句在没有条件符合时执行，这也就意味着 `selects` 永远不会被阻塞。）依靠带缓冲的信道和垃圾回收器的记录， 我们仅用短短几行代码就构建了一个限流漏桶。
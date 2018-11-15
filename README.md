# kivy与原生控件混编

## 前言

### 阅读下面内容必须具备的前置知识： 
 
- java语法基础
- 原生安卓编程基础
- kivy语法基础
- jnius语法基础

### 混编前景

理论上可以完全使用原生布局和控件编写界面，那么kivy就只负责逻辑部分，现在的原生控件编写方法没有借助xml，还显得比较丑，可以使用原生语法编写布局xml，然后通过sax解析使用。有了混编就不需要为kivy 中文支持添加字体，缩小了apk体积。未来不可限量，一切皆有可能。


## 0x01 思路

核心思路是用一个widget封装一个原生控件，通过widget构造方法传入控件位置、大小参数，用Clock.schedule_once调用原生控件初始化方法（因为原生控件必须在ui线程中运行，所以只能用clock执行一个线程，用@run_on_ui_thread装饰。）

原生控件构造方法里，实例化原生控件，设置位置、大小，以及其他属性，设置事件监听器。通过python的activity. addContentView将实例化的原生控件增加到界面中。
把原生控件作为widget的成员变量，方便之后在widget以外的地方访问。


## 0x02 示例

下面以edittext编辑框为例，封装edittext的类同时继承Widget、EventDispatcher，Widget是为了作为kivy控件实现占位作用，EventDispatcher是为了让该类具备注册事件、处理事件、回调事件的作用。

```
class pyEditText(Widget,EventDispatcher):  
    _edittext_events = ['on_edittext']
                 
    def __init__(self, **kwargs):                        
        super(pyEditText, self).__init__(**kwargs)
        self.edittextWidth = kwargs.get('width') if kwargs.has_key('width') else LayoutParams.MATCH_PARENT
        self.edittextPosX = kwargs.get('posX') if kwargs.has_key('posX') else 0 
        self.edittextPosY = kwargs.get('posY') if kwargs.has_key('posY') else 0
        self.edittextHeight = kwargs.get('height') if kwargs.has_key('height') else LayoutParams.MATCH_PARENT               
        
        self._register_events()
        Clock.schedule_once(self.create_edittext, 0)
    
    @run_on_ui_thread                      
    def create_edittext(self, *args):    
        edittext = EditText(activity)
       
        edittext.setX(self.edittextPosX)
        edittext.setY(self.edittextPosY)
        hinttext = '支持emoji，回车后弹出toast'.decode('utf-8')
        cstext = cast('java.lang.CharSequence', javaString(hinttext))
        edittext.setHint(cstext)
        edittext.setTextSize(14)
        edittext.setLayoutParams(LayoutParams(LayoutParams.WRAP_CONTENT,
        LayoutParams.WRAP_CONTENT))
        activity.addContentView(edittext, LayoutParams(self.edittextWidth,self.edittextHeight))         
        self.editcore = edittext
        edittext.setOnEditorActionListener(ListenerCore(self))
      
        
    def _register_events(self):
        events = self._edittext_events
        for event_name in events:

            #create the default handler
            setattr(self,event_name,self._event_default_handler)
            
            #register the event 
            self.register_event_type(event_name)    
    
    def dispatch_event(self,event_name,**kwargs):
        self.dispatch(event_name,**kwargs)
        print('--- Eevent %s dispatched \n' %event_name, kwargs)

    def _event_default_handler(self,**kwargs):
        pass
```

事件监听器ListenerCore，因为事件监听器都是接口，所以通过jnius.PythonJavaClass实现。如下：

```
class ListenerCore(PythonJavaClass):

    __javacontext__ = 'app'
    __javainterfaces__ = ['android.widget.TextView$OnEditorActionListener']
 
    #Constructor 
    def __init__(self,edittext_obj):
        super(ListenerCore,self).__init__()
        self._edittext = edittext_obj
                

    @java_method('(Landroid/widget/TextView;ILandroid/view/KeyEvent;)Z')
    def onEditorAction(self, view, arg1, arg2):
        self._edittext.dispatch_event(
                                        'on_edittext',
                                         view=view,
                                         actionId=arg1,
                                         keyevent=arg2
                                        )
```

在py中定义java class需要通过继承`PythonJavaClass`实现，并且只能用于实现java的接口，无法重写java类。在定义开头必须写明`__javacontext__`，对于android平台必须是app，默认是system。`__javainterfaces__`是要实现的接口名。

在构造方法中获取下edittext对象，重写事件回调方法`onEditorAction`，这里使用edittext回调接收到事件，方便在主逻辑中实现具体的回调方法。增强这个事件监听器的复用性。

语法说明：

- `@java_method`，用于修饰java方法，后面是参数列表，遵循java的符号定义，和smali语法大同小异。

- `Landroid/widget/TextView;` 对应view，L代表后面是对象
。
- `I `  对应arg1，`I`代表`java/lang/Integer;`

- `Landroid/view/KeyEvent; ` 对应arg2

- `Z`是返回值类型，代表 `java/lang/Boolean;`

其他符号列表可以参考jnius文档，Java signature format一节，如下：

- L<java class>; = represent a Java object of the type <java class>
- Z = represent a java/lang/Boolean;
- B = represent a java/lang/Byte;
- C = represent a java/lang/Character;
- S = represent a java/lang/Short;
- I = represent a java/lang/Integer;
- J = represent a java/lang/Long;
- F = represent a java/lang/Float;
- D = represent a java/lang/Double;
- V = represent void, available only for the return type

所以类型都可以在前面加上`[`表示数组类型。


在主界面里实例化edittext，并且绑定事件处理方法。这里还实现了一个原生toast。运行后在编辑框输入文本后回车就会看到一个输入内容的toast。toast接收的字符串是CharSequence类型，需要用cast函数做一个映射。

```
class MainLayout(BoxLayout):
    def __init__(self, **kwargs):                         
        super(MainLayout, self).__init__(**kwargs)     
        Clock.schedule_once(self.init_window, 0)
 
    @run_on_ui_thread
    def init_window(self,dt):
        self.pyedit = pyEditText(posX=0,
                         posY=0,
                         width=Window.width,
                         height=self.txtinput.height)
    
        self.txtinput.add_widget(self.pyedit)
        self.pyedit.bind(on_edittext= self.edittext_callback)   

    def edittext_callback(self, *args, **kwargs):
        actionId = kwargs.get('actionId')
        inputtext = ''.join(self.pyedit.editcore.getText().split('\n'))
        if not actionId:
            self.toast(inputtext)
        else:
            return False

    @run_on_ui_thread
    def toast(self,text, length_long=False):
        duration = Toast.LENGTH_LONG if length_long else Toast.LENGTH_SHORT
        c = text.decode('utf-8')
        c = cast('java.lang.CharSequence', javaString(c))
        t = Toast.makeText(activity, c, duration)
        t.show()
```

### 查看参数对应的符号

使用javap命令：

```
javap -s java.util.Iterator
```

查看安卓类库参数需要切换到安卓sdk/platforms/android-xx下面使用命令：

```
javap -s -classpath android.jar android.app.Activity
```


代码和打包的apk已经上传，供测试。

#### **大佬们救救孩子吧，现在可以捐助作者了，捐助我有机会看到更多教程。**

<img src="https://i.imgur.com/94DkJbs.jpg" width = "600" height = "350" alt="捐助up" align=center />
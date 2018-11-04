#-*-coding:utf8;-*-
#qpy:2
#qpy:kivy
          
from kivy.app import App                        
from kivy.uix.widget import Widget
from kivy.clock import Clock                   
from jnius import autoclass, cast,PythonJavaClass,java_method
from android.runnable import run_on_ui_thread     
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.event import EventDispatcher 

 
activity = autoclass('org.kivy.android.PythonActivity').mActivity                              
LayoutParams = autoclass('android.view.ViewGroup$LayoutParams')
Toast = autoclass('android.widget.Toast')
EditText = autoclass('android.widget.EditText')
javaString = autoclass('java.lang.String')
EditorInfo = autoclass('android.view.inputmethod.EditorInfo')
SingleLineTransformationMethod =autoclass('android.text.method.SingleLineTransformationMethod')

class ListenerCore(PythonJavaClass):

    __javacontext__ = 'app'
    __javainterfaces__ = ['android/widget/TextView$OnEditorActionListener']
 
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
        hinttext = '支持emoji，输入内容后回车弹出toast'.decode('utf-8')
        cstext = cast('java.lang.CharSequence', javaString(hinttext))
        edittext.setHint(cstext)
        edittext.setMaxLines(1)
        edittext.setTransformationMethod(SingleLineTransformationMethod.getInstance())
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
        
class MainApp(App):                                                                          
    def build(self):              
        return MainLayout()                                                                             

if __name__ == '__main__':                          
        MainApp().run()

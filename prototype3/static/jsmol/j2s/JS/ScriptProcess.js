Clazz.declarePackage("JS");
(function(){
var c$ = Clazz.decorateAsClass(function(){
this.processName = null;
this.context = null;
Clazz.instantialize(this, arguments);}, JS, "ScriptProcess", null);
Clazz.makeConstructor(c$, 
function(name, context){
this.processName = name;
this.context = context;
}, "~S,JS.ScriptContext");
})();
;//5.0.1-v7 Wed Apr 02 04:50:42 CDT 2025

Clazz.declarePackage("JSV.common");
(function(){
var c$ = Clazz.decorateAsClass(function(){
this.isub = 0;
this.title = null;
Clazz.instantialize(this, arguments);}, JSV.common, "SubSpecChangeEvent", null);
Clazz.makeConstructor(c$, 
function(isub, title){
this.isub = isub;
this.title = title;
}, "~N,~S");
Clazz.defineMethod(c$, "isValid", 
function(){
return (this.title != null);
});
Clazz.defineMethod(c$, "getSubIndex", 
function(){
return this.isub;
});
Clazz.overrideMethod(c$, "toString", 
function(){
return this.title;
});
})();
;//5.0.1-v7 Wed Apr 02 04:50:42 CDT 2025

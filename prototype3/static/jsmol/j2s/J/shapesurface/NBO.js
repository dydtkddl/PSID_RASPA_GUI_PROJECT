Clazz.declarePackage("J.shapesurface");
Clazz.load(["J.shapesurface.MolecularOrbital"], "J.shapesurface.NBO", null, function(){
var c$ = Clazz.declareType(J.shapesurface, "NBO", J.shapesurface.MolecularOrbital);
Clazz.defineMethod(c$, "initShape", 
function(){
Clazz.superCall(this, J.shapesurface.NBO, "initShape", []);
this.myType = "nbo";
this.setPropI("thisID", "nbo", null);
});
});
;//5.0.1-v7 Wed Apr 02 04:50:42 CDT 2025

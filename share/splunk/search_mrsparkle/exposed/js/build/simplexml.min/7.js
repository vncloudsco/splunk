(window.webpackJsonp=window.webpackJsonp||[]).push([[7],{"splunkjs/contrib/jquery.sortable.html5":function(module,exports,__webpack_require__){var __WEBPACK_AMD_DEFINE_ARRAY__,__WEBPACK_AMD_DEFINE_RESULT__;__WEBPACK_AMD_DEFINE_ARRAY__=[__webpack_require__("shim/jquery"),__webpack_require__("require/underscore")],void 0===(__WEBPACK_AMD_DEFINE_RESULT__=function(jQuery,_){var $,dragging,placeholders;placeholders=($=jQuery)(),$.fn.sortable5=function(options){var method=String(options);return options=$.extend({connectWith:!1},options),this.each(function(){if(/^enable|disable|destroy$/.test(method)){var items=$(this).children($(this).data("items")).attr("draggable","enable"==method);"destroy"==method&&items.add(this).removeData("connectWith items").removeAttr("draggable").off("dragstart.h5s dragend.h5s selectstart.h5s dragover.h5s dragenter.h5s drop.h5s")}else{items=$(this).children(options.items);var isHandle,placeholderFactory=options.placeholder,that=this;_.isString(placeholderFactory)&&(placeholderFactory={element:function(){return $("<"+(/^ul|ol$/i.test(that.tagName)?"li":"div")+' class="sortable-placeholder"><div class="dashboard-panel"></div></div>')},update:function(ct,item){}});var placeholder=placeholderFactory.element();items.find(options.handle).mousedown(function(){isHandle=!0}).mouseup(function(){isHandle=!1}),$(this).data("items",options.items),placeholders=placeholders.add(placeholder),options.connectWith&&$(options.connectWith).add(this).data("connectWith",options.connectWith),items.attr("draggable","true").on("dragstart.h5s",function(e){if(options.handle&&!isHandle)return!1;isHandle=!1;var dt=e.originalEvent.dataTransfer;dt.effectAllowed="move",dt.setData("Text","dummy"),(dragging=$(this)).addClass("sortable-dragging").index()}).on("dragend.h5s",function(){dragging&&(dragging.removeClass("sortable-dragging").show(),placeholders.detach(),dragging.parent().trigger("sortupdate",{item:dragging}),dragging=null)}).not("a[href], img").on("selectstart.h5s",function(){return this.dragDrop&&this.dragDrop(),!1}).end().add([this,placeholder]).on("dragover.h5s dragenter.h5s drop.h5s",function(e){if(!items.is(dragging)&&options.connectWith!==$(dragging).parent().data("connectWith"))return!0;if("drop"==e.type){e.stopPropagation();var p=placeholders.filter(":visible").after(dragging);return placeholderFactory.update(null,p),dragging.trigger("dragend.h5s"),!1}return e.preventDefault(),e.originalEvent.dataTransfer.dropEffect="move",items.is(this)?(options.forcePlaceholderSize&&placeholder.height(dragging.outerHeight()),dragging.hide(),$(this)[placeholder.index()<$(this).index()?"after":"before"](placeholder),placeholders.not(placeholder).detach(),placeholderFactory.update(null,placeholder),dragging.trigger("sort")):placeholders.is(this)||$(this).children(options.items).length||(placeholders.detach(),$(this).append(placeholder),placeholderFactory.update(null,placeholder),dragging.trigger("sort")),!1})}})}}.apply(exports,__WEBPACK_AMD_DEFINE_ARRAY__))||(module.exports=__WEBPACK_AMD_DEFINE_RESULT__)}}]);
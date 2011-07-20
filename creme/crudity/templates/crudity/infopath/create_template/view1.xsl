<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:my="{{ creme_namespace }}" xmlns:xd="http://schemas.microsoft.com/office/infopath/2003" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:msxsl="urn:schemas-microsoft-com:xslt" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns:xdExtension="http://schemas.microsoft.com/office/infopath/2003/xslt/extension" xmlns:xdXDocument="http://schemas.microsoft.com/office/infopath/2003/xslt/xDocument" xmlns:xdSolution="http://schemas.microsoft.com/office/infopath/2003/xslt/solution" xmlns:xdFormatting="http://schemas.microsoft.com/office/infopath/2003/xslt/formatting" xmlns:xdImage="http://schemas.microsoft.com/office/infopath/2003/xslt/xImage" xmlns:xdUtil="http://schemas.microsoft.com/office/infopath/2003/xslt/Util" xmlns:xdMath="http://schemas.microsoft.com/office/infopath/2003/xslt/Math" xmlns:xdDate="http://schemas.microsoft.com/office/infopath/2003/xslt/Date" xmlns:sig="http://www.w3.org/2000/09/xmldsig#" xmlns:xdSignatureProperties="http://schemas.microsoft.com/office/infopath/2003/SignatureProperties" xmlns:ipApp="http://schemas.microsoft.com/office/infopath/2006/XPathExtension/ipApp" xmlns:xdEnvironment="http://schemas.microsoft.com/office/infopath/2006/xslt/environment" xmlns:xdUser="http://schemas.microsoft.com/office/infopath/2006/xslt/User">
	<xsl:output method="html" indent="no"/>
	<xsl:template match="my:CremeCRMCrudity">
		<html>
			<head>
				<meta content="text/html" http-equiv="Content-Type"></meta>
				<style controlStyle="controlStyle">@media screen 			{ 			BODY{margin-left:21px;background-position:21px 0px;} 			} 		BODY{color:windowtext;background-color:window;layout-grid:none;} 		.xdListItem {display:inline-block;width:100%;vertical-align:text-top;} 		.xdListBox,.xdComboBox{margin:1px;} 		.xdInlinePicture{margin:1px; BEHAVIOR: url(#default#urn::xdPicture) } 		.xdLinkedPicture{margin:1px; BEHAVIOR: url(#default#urn::xdPicture) url(#default#urn::controls/Binder) } 		.xdSection{border:1pt solid #FFFFFF;margin:6px 0px 6px 0px;padding:1px 1px 1px 5px;} 		.xdRepeatingSection{border:1pt solid #FFFFFF;margin:6px 0px 6px 0px;padding:1px 1px 1px 5px;} 		.xdMultiSelectList{margin:1px;display:inline-block; border:1pt solid #dcdcdc; padding:1px 1px 1px 5px; text-indent:0; color:windowtext; background-color:window; overflow:auto; behavior: url(#default#DataBindingUI) url(#default#urn::controls/Binder) url(#default#MultiSelectHelper) url(#default#ScrollableRegion);} 		.xdMultiSelectListItem{display:block;white-space:nowrap}		.xdMultiSelectFillIn{display:inline-block;white-space:nowrap;text-overflow:ellipsis;;padding:1px;margin:1px;border: 1pt solid #dcdcdc;overflow:hidden;text-align:left;}		.xdBehavior_Formatting {BEHAVIOR: url(#default#urn::controls/Binder) url(#default#Formatting);} 	 .xdBehavior_FormattingNoBUI{BEHAVIOR: url(#default#CalPopup) url(#default#urn::controls/Binder) url(#default#Formatting);} 	.xdExpressionBox{margin: 1px;padding:1px;word-wrap: break-word;text-overflow: ellipsis;overflow-x:hidden;}.xdBehavior_GhostedText,.xdBehavior_GhostedTextNoBUI{BEHAVIOR: url(#default#urn::controls/Binder) url(#default#TextField) url(#default#GhostedText);}	.xdBehavior_GTFormatting{BEHAVIOR: url(#default#urn::controls/Binder) url(#default#Formatting) url(#default#GhostedText);}	.xdBehavior_GTFormattingNoBUI{BEHAVIOR: url(#default#CalPopup) url(#default#urn::controls/Binder) url(#default#Formatting) url(#default#GhostedText);}	.xdBehavior_Boolean{BEHAVIOR: url(#default#urn::controls/Binder) url(#default#BooleanHelper);}	.xdBehavior_Select{BEHAVIOR: url(#default#urn::controls/Binder) url(#default#SelectHelper);}	.xdBehavior_ComboBox{BEHAVIOR: url(#default#ComboBox)} 	.xdBehavior_ComboBoxTextField{BEHAVIOR: url(#default#ComboBoxTextField);} 	.xdRepeatingTable{BORDER-TOP-STYLE: none; BORDER-RIGHT-STYLE: none; BORDER-LEFT-STYLE: none; BORDER-BOTTOM-STYLE: none; BORDER-COLLAPSE: collapse; WORD-WRAP: break-word;}.xdScrollableRegion{BEHAVIOR: url(#default#ScrollableRegion);} 		.xdLayoutRegion{display:inline-block;} 		.xdMaster{BEHAVIOR: url(#default#MasterHelper);} 		.xdActiveX{margin:1px; BEHAVIOR: url(#default#ActiveX);} 		.xdFileAttachment{display:inline-block;margin:1px;BEHAVIOR:url(#default#urn::xdFileAttachment);} 		.xdPageBreak{display: none;}BODY{margin-right:21px;} 		.xdTextBoxRTL{display:inline-block;white-space:nowrap;text-overflow:ellipsis;;padding:1px;margin:1px;border: 1pt solid #dcdcdc;color:windowtext;background-color:window;overflow:hidden;text-align:right;word-wrap:normal;} 		.xdRichTextBoxRTL{display:inline-block;;padding:1px;margin:1px;border: 1pt solid #dcdcdc;color:windowtext;background-color:window;overflow-x:hidden;word-wrap:break-word;text-overflow:ellipsis;text-align:right;font-weight:normal;font-style:normal;text-decoration:none;vertical-align:baseline;} 		.xdDTTextRTL{height:100%;width:100%;margin-left:22px;overflow:hidden;padding:0px;white-space:nowrap;} 		.xdDTButtonRTL{margin-right:-21px;height:18px;width:20px;behavior: url(#default#DTPicker);} 		.xdMultiSelectFillinRTL{display:inline-block;white-space:nowrap;text-overflow:ellipsis;;padding:1px;margin:1px;border: 1pt solid #dcdcdc;overflow:hidden;text-align:right;}.xdTextBox{display:inline-block;white-space:nowrap;text-overflow:ellipsis;;padding:1px;margin:1px;border: 1pt solid #dcdcdc;color:windowtext;background-color:window;overflow:hidden;text-align:left;word-wrap:normal;} 		.xdRichTextBox{display:inline-block;;padding:1px;margin:1px;border: 1pt solid #dcdcdc;color:windowtext;background-color:window;overflow-x:hidden;word-wrap:break-word;text-overflow:ellipsis;text-align:left;font-weight:normal;font-style:normal;text-decoration:none;vertical-align:baseline;} 		.xdDTPicker{;display:inline;margin:1px;margin-bottom: 2px;border: 1pt solid #dcdcdc;color:windowtext;background-color:window;overflow:hidden;text-indent:0} 		.xdDTText{height:100%;width:100%;margin-right:22px;overflow:hidden;padding:0px;white-space:nowrap;} 		.xdDTButton{margin-left:-21px;height:18px;width:20px;behavior: url(#default#DTPicker);} 		.xdRepeatingTable TD {VERTICAL-ALIGN: top;}</style>
				<style tableEditor="TableStyleRulesID">TABLE.xdLayout TD {
	BORDER-BOTTOM: medium none; BORDER-LEFT: medium none; BORDER-TOP: medium none; BORDER-RIGHT: medium none
}
TABLE.msoUcTable TD {
	BORDER-BOTTOM: 1pt solid; BORDER-LEFT: 1pt solid; BORDER-TOP: 1pt solid; BORDER-RIGHT: 1pt solid
}
TABLE {
	BEHAVIOR: url (#default#urn::tables/NDTable)
}
</style>
				<style languageStyle="languageStyle">BODY {
	FONT-FAMILY: Verdana; FONT-SIZE: 10pt
}
TABLE {
	FONT-FAMILY: Verdana; FONT-SIZE: 10pt
}
SELECT {
	FONT-FAMILY: Verdana; FONT-SIZE: 10pt
}
.optionalPlaceholder {
	FONT-STYLE: normal; PADDING-LEFT: 20px; FONT-FAMILY: Verdana; COLOR: #333333; FONT-SIZE: xx-small; FONT-WEIGHT: normal; TEXT-DECORATION: none; BEHAVIOR: url(#default#xOptional)
}
.langFont {
	FONT-FAMILY: Verdana
}
.defaultInDocUI {
	FONT-FAMILY: Verdana; FONT-SIZE: xx-small
}
.optionalPlaceholder {
	PADDING-RIGHT: 20px
}
</style>
				<style themeStyle="urn:office.microsoft.com:themeBlue">BODY {
	BACKGROUND-COLOR: white; COLOR: black
}
TABLE {
	BORDER-BOTTOM: medium none; BORDER-LEFT: medium none; BORDER-COLLAPSE: collapse; BORDER-TOP: medium none; BORDER-RIGHT: medium none
}
TD {
	BORDER-BOTTOM-COLOR: #517dbf; BORDER-TOP-COLOR: #517dbf; BORDER-RIGHT-COLOR: #517dbf; BORDER-LEFT-COLOR: #517dbf
}
TH {
	BORDER-BOTTOM-COLOR: #517dbf; BACKGROUND-COLOR: #cbd8eb; BORDER-TOP-COLOR: #517dbf; COLOR: black; BORDER-RIGHT-COLOR: #517dbf; BORDER-LEFT-COLOR: #517dbf
}
.xdTableHeader {
	BACKGROUND-COLOR: #ebf0f9; COLOR: black
}
P {
	MARGIN-TOP: 0px
}
H1 {
	MARGIN-TOP: 0px; MARGIN-BOTTOM: 0px; COLOR: #1e3c7b
}
H2 {
	MARGIN-TOP: 0px; MARGIN-BOTTOM: 0px; COLOR: #1e3c7b
}
H3 {
	MARGIN-TOP: 0px; MARGIN-BOTTOM: 0px; COLOR: #1e3c7b
}
H4 {
	MARGIN-TOP: 0px; MARGIN-BOTTOM: 0px; COLOR: #1e3c7b
}
H5 {
	MARGIN-TOP: 0px; MARGIN-BOTTOM: 0px; COLOR: #517dbf
}
H6 {
	MARGIN-TOP: 0px; MARGIN-BOTTOM: 0px; COLOR: #ebf0f9
}
.primaryVeryDark {
	BACKGROUND-COLOR: #1e3c7b; COLOR: #ebf0f9
}
.primaryDark {
	BACKGROUND-COLOR: #517dbf; COLOR: white
}
.primaryMedium {
	BACKGROUND-COLOR: #cbd8eb; COLOR: black
}
.primaryLight {
	BACKGROUND-COLOR: #ebf0f9; COLOR: black
}
.accentDark {
	BACKGROUND-COLOR: #517dbf; COLOR: white
}
.accentLight {
	BACKGROUND-COLOR: #ebf0f9; COLOR: black
}
</style>
			</head>
			<body style="BACKGROUND-COLOR: #ffffff; COLOR: #000000">
				<div> </div>
				<div>
					<table style="BORDER-BOTTOM-STYLE: none; BORDER-LEFT-STYLE: none; WIDTH: 589px; BORDER-COLLAPSE: collapse; WORD-WRAP: break-word; BORDER-TOP-STYLE: none; TABLE-LAYOUT: fixed; BORDER-RIGHT-STYLE: none" class="xdFormLayout xdLayout" border="1">
						<colgroup>
							<col style="WIDTH: 589px"></col>
						</colgroup>
						<tbody vAlign="top">
							<tr style="MIN-HEIGHT: 20px" class="primaryVeryDark">
								<td style="BORDER-BOTTOM: 5pt solid; BACKGROUND-COLOR: #94c6db; BORDER-LEFT-STYLE: none; BORDER-TOP-STYLE: none; BORDER-RIGHT-STYLE: none">
									<div>
										<table style="BORDER-BOTTOM: medium none; BORDER-LEFT: medium none; WIDTH: 586px; BORDER-COLLAPSE: collapse; WORD-WRAP: break-word; TABLE-LAYOUT: fixed; BORDER-TOP: medium none; BORDER-RIGHT: medium none" class="xdLayout" border="1" borderColor="buttontext">
											<colgroup>
												<col style="WIDTH: 207px"></col>
												<col style="WIDTH: 379px"></col>
											</colgroup>
											<tbody vAlign="top">
												<tr>
													<td>
														<div>
															<font color="#ebf0f9" size="4" face="Verdana">
																<img style="WIDTH: 182px; HEIGHT: 50px" src="creme.png" width="366" height="100"/>
															</font>
														</div>
													</td>
													<td style="PADDING-BOTTOM: 1px; PADDING-LEFT: 1px; PADDING-RIGHT: 1px; VERTICAL-ALIGN: middle; PADDING-TOP: 1px">
														<div>
															<font color="#ffffff" size="4">
																<strong>{{ form_title }}</strong>
															</font>
														</div>
													</td>
												</tr>
											</tbody>
										</table>
									</div>
								</td>
							</tr>
							<tr style="MIN-HEIGHT: 2.573in" class="primarylight">
								<td vAlign="top" style="BORDER-BOTTOM-STYLE: none; TEXT-ALIGN: left; BACKGROUND-COLOR: #f6fcff; BORDER-LEFT-STYLE: none; BORDER-RIGHT-STYLE: none; BORDER-TOP: 5pt solid">
									<div><xsl:apply-templates select="." mode="_1"/>
									</div>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
				<div> </div>
			</body>
		</html>
	</xsl:template>
	<xsl:template match="my:CremeCRMCrudity" mode="_1">
		<div style="WIDTH: 583px; MARGIN-BOTTOM: 6px; HEIGHT: 251px;" class="xdSection xdRepeating" title="" align="left" xd:CtrlId="CTRL1" xd:xctname="Section" tabIndex="-1">
			<div align="left">
				<table style="BORDER-BOTTOM: medium none; BORDER-LEFT: medium none; WIDTH: 574px; BORDER-COLLAPSE: collapse; WORD-WRAP: break-word; TABLE-LAYOUT: fixed; BORDER-TOP: medium none; BORDER-RIGHT: medium none" class="xdLayout" border="1" borderColor="buttontext">
					<colgroup>
						<col style="WIDTH: 287px"></col>
						<col style="WIDTH: 287px"></col>
					</colgroup>
					<tbody vAlign="top">
                        {% for field in fields %}
                            {% with field.get_view_element as view_element %}
                                {% if view_element %}
                                    <tr>
                                        <td style="BACKGROUND-COLOR: {% cycle "#b3d2df" "#bdd8e4"%}">
                                            <div>
                                                <font color="#376e86" size="2" face="Verdana">
                                                    <strong>{{ field.model_field.verbose_name }}</strong>
                                                </font>
                                            </div>
                                        </td>
                                        <td style="BACKGROUND-COLOR: {% cycle "#e6f2f7" "#f4fafd"%}">
                                            <div>
                                                <font size="2" face="Verdana">{{ view_element }}</font>
                                            </div>
                                        </td>
                                    </tr>
                                {% endif %}
                            {% endwith %}
                        {% endfor %}
					</tbody>
				</table>
			</div>
			<div>
				<input style="BEHAVIOR: url(#default#ActionButton)" class="langFont" title="" value="Envoyer" type="button" xd:CtrlId="CTRL15_5" xd:xctname="Button" xd:action="submit" tabIndex="0"/>
			</div>
			<div> </div>
		</div>
	</xsl:template>
</xsl:stylesheet>

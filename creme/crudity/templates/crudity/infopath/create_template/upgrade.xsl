<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:msxsl="urn:schemas-microsoft-com:xslt" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:my="{{ creme_namespace }}" xmlns:xd="http://schemas.microsoft.com/office/infopath/2003" version="1.0">
	<xsl:output encoding="UTF-8" method="xml"/>
	<xsl:template match="text() | *[namespace-uri()='http://www.w3.org/1999/xhtml']" mode="RichText">
		<xsl:copy-of select="."/>
	</xsl:template>
	<xsl:template match="/">
		<xsl:copy-of select="processing-instruction() | comment()"/>
		<xsl:choose>
			<xsl:when test="my:CremeCRMCrudity">
				<xsl:apply-templates select="my:CremeCRMCrudity" mode="_0"/>
			</xsl:when>
			<xsl:otherwise>
				<xsl:variable name="var">
					<xsl:element name="my:CremeCRMCrudity"/>
				</xsl:variable>
				<xsl:apply-templates select="msxsl:node-set($var)/*" mode="_0"/>
			</xsl:otherwise>
		</xsl:choose>
	</xsl:template>
    {% for field in fields %}
        {% if field.xsl_element and field.is_m2m_field %}
            {% with field.name as field_name %}
            	<xsl:template match="my:{{ field_name }}_value" mode="_2">
                    <xsl:copy>
                        <xsl:copy-of select="./text()[1]"/>
                        <xsl:copy-of select="./@xsi:nil"/>
                    </xsl:copy>
                </xsl:template>
                <xsl:template match="my:{{ field_name }}" mode="_1">
                    <xsl:copy>
                        <xsl:choose>
                            <xsl:when test="my:{{ field_name }}_value">
                                <xsl:apply-templates select="my:{{ field_name }}_value" mode="_2"/>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:variable name="var">
                                    <xsl:element name="my:{{ field_name }}_value">
                                        <xsl:attribute name="xsi:nil">true</xsl:attribute>
                                    </xsl:element>
                                </xsl:variable>
                                <xsl:apply-templates select="msxsl:node-set($var)/*" mode="_2"/>
                            </xsl:otherwise>
                        </xsl:choose>
                    </xsl:copy>
                </xsl:template>
            {% endwith %}
        {% endif %}
    {% endfor %}
    <xsl:template match="my:CremeCRMCrudity" mode="_0">
		<xsl:copy>
            {% for field in fields %}
                {{ field.xsl_element|default_if_none:"" }}
            {% endfor %}
		</xsl:copy>
	</xsl:template>
</xsl:stylesheet>

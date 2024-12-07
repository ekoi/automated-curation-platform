<?xml version="1.0"?>
<xsl:stylesheet
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:math="http://www.w3.org/2005/xpath-functions/math"
    xmlns:ns0="http://www.openarchives.org/OAI/2.0/"
    xmlns:ns1="http://datacite.org/schema/kernel-4"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:oai="http://www.openarchives.org/OAI/2.0/"
    xmlns:ddi="ddi:codebook:2_5"
    exclude-result-prefixes="xs math" version="3.0">
    <xsl:output indent="yes" omit-xml-declaration="yes" />


    <xsl:template match="/"
        xpath-default-namespace="http://www.w3.org/2005/xpath-functions">

        {
        "datasetVersion": {
        "datasetPersistentId":"<xsl:value-of select="//ns1:identifier"/>",
        <xsl:variable name="dateTime" select="//ns0:datestamp" />
       "publicationDate": "<xsl:value-of select="substring-before($dateTime, 'T')" />",
       "termsOfUse": "<xsl:value-of select="//ns1:rights/@rightsURI"/>\n<xsl:value-of select="//ns1:rights"/>",
       <xsl:text disable-output-escaping="yes">"dataAccessPlace": "&lt;a href=\&quot;https://dab.surf.nl/dataset?pid=doi:</xsl:text><xsl:value-of select="//ns1:identifier"/><xsl:text disable-output-escaping="yes">\&quot;&gt;https://dab.surf.nl/dataset?pid=doi:</xsl:text><xsl:value-of select="//ns1:identifier"/><xsl:text disable-output-escaping="yes">&lt;/a&gt;",</xsl:text>
       "metadataBlocks": {
        "citation": {
        "fields": [
        {
        "value": "<xsl:value-of select="normalize-space(replace(//ns1:title, '&quot;', '\\&quot;'))"/>",
        "typeClass": "primitive",
        "multiple": false,
        "typeName": "title"
        },
        {
        "value": [
        <xsl:variable name="publisher" select="//ns1:publisher" />
        <xsl:for-each select="//ns1:creators/ns1:creator">
        {
        "authorName": {
        "value": "<xsl:value-of select="normalize-space(replace(./ns1:creatorName, '&quot;', '\\&quot;'))"/>",
        "typeClass": "primitive",
        "multiple": false,
        "typeName": "authorName"
        },
        "authorAffiliation": {
        "value": "<xsl:value-of select="$publisher"/>",
        "typeClass": "primitive",
        "multiple": false,
        "typeName": "authorAffiliation"
        }
        }
            <xsl:if test="position() != last()">
                <xsl:text>,</xsl:text>
            </xsl:if>
        </xsl:for-each>
        ],
        "typeClass": "compound",
        "multiple": true,
        "typeName": "author"
        },
        {
        "value": [
        { "datasetContactEmail" : {
        "typeClass": "primitive",
        "multiple": false,
        "typeName": "datasetContactEmail",
        "value" : "portal@odissei.nl"
        },
        "datasetContactName" : {
        "typeClass": "primitive",
        "multiple": false,
        "typeName": "datasetContactName",
        "value": ""
        }
        }],
        "typeClass": "compound",
        "multiple": true,
        "typeName": "datasetContact"
        },
        {
        "value": [ {
        "dsDescriptionValue":{
        "value":   "<xsl:value-of select="normalize-space(replace(//ns1:description, '&quot;', '\\&quot;'))"/>",
        "multiple":false,
        "typeClass": "primitive",
        "typeName": "dsDescriptionValue"
        }}],
        "typeClass": "compound",
        "multiple": true,
        "typeName": "dsDescription"
        },
        {
        "value": [
        "Social Sciences"
        ],
        "typeClass": "controlledVocabulary",
        "multiple": true,
        "typeName": "subject"
        },
        {
        "typeName": "keyword",
        "multiple": true,
        "typeClass": "compound",
        "value": [
        <xsl:for-each select="//ns1:subject[@subjectScheme='CID keyword']">
                    {
                    "keywordValue": {
                    "typeName": "keywordValue",
                    "multiple": false,
                    "typeClass": "primitive",
                    "value": "<xsl:value-of select="."/>"
                    }
                    }
            <xsl:if test="position() != last()">
                <xsl:text>,</xsl:text>
            </xsl:if>
        </xsl:for-each>
        ]
        }
        ,
        {
        "typeName": "topicClassification",
        "multiple": true,
        "typeClass": "compound",
        "value": [
        <xsl:for-each select="//ns1:subject[@subjectScheme='CID construct']">
        {
        "topicClassValue": {
        "typeName": "topicClassValue",
        "multiple": false,
        "typeClass": "primitive",
        "value": "<xsl:value-of select="."/>"
        }
        }
            <xsl:if test="position() != last()">
                <xsl:text>,</xsl:text>
            </xsl:if>
        </xsl:for-each>
        ]
        },
        <xsl:for-each select="//ns1:relatedIdentifier">
        {
        "typeName": "publication",
        "multiple": true,
        "typeClass": "compound",
        "value": [
        {
        "publicationIDType": {
        "typeName": "publicationIDType",
        "multiple": false,
        "typeClass": "controlledVocabulary",
        "value": "doi"
        },
        "publicationIDNumber": {
        "typeName": "publicationIDNumber",
        "multiple": false,
        "typeClass": "primitive",
        "value":
            <xsl:choose>
                <xsl:when test="substring-after(.,'doi.org/')">
                    "<xsl:value-of select="substring-after(.,'doi.org/')"/>"
                </xsl:when>
                <xsl:otherwise>
                    "<xsl:value-of select="."/>"
                </xsl:otherwise>
            </xsl:choose>
        },
        "publicationURL": {
        "typeName": "publicationURL",
        "multiple": false,
	    "typeClass": "primitive",
        "value":
            <xsl:choose>
                <xsl:when test="substring-after(.,'doi.org/')">
                    "https://doi.org/<xsl:value-of select="substring-after(.,'doi.org/')"/>"
                </xsl:when>
                <xsl:otherwise>
                    "https://doi.org/<xsl:value-of select="."/>"
                </xsl:otherwise>
            </xsl:choose>
        }
        }
        ]
        },
        </xsl:for-each>
        {
        "typeName": "language",
        "multiple": true,
        "typeClass": "controlledVocabulary",
        "value": ["English"]
        },
        {
        "typeName": "dateOfCollection",
        "multiple": true,
        "typeClass": "compound",
        "value": [
        <xsl:for-each select="//ns1:date">
            <xsl:variable name="coldate-before">
                <xsl:value-of select="substring-before(., '/')"/>
            </xsl:variable>
            <xsl:variable name="coldate-after">
                <xsl:value-of select="substring-after(., '/')"/>
            </xsl:variable>
        {
        "dateOfCollectionStart": {
        "typeName": "dateOfCollectionStart",
        "multiple": false,
        "typeClass": "primitive",
        "value": "<xsl:value-of select="$coldate-before"/>"
        },
        "dateOfCollectionEnd": {
        "typeName": "dateOfCollectionEnd",
        "multiple": false,
        "typeClass": "primitive",
        "value": "<xsl:value-of select="$coldate-after"/>"
        }
        }
            <xsl:if test="position() != last()">
                <xsl:text>,</xsl:text>
            </xsl:if>
        </xsl:for-each>
        ]
        }
        ],
        "displayName": "Citation Metadata"
        },
        <xsl:if test="//ns1:geoLocationPlace">
        "geospatial": {
        "displayName": "Geospatial Metadata",
        "name": "geospatial",
        "fields": [
        {
        "typeName": "geographicCoverage",
        "multiple": true,
        "typeClass": "compound",
        "value": [
        {
        "country": {
        "typeName": "country",
        "multiple": false,
        "typeClass": "controlledVocabulary",
        "value": "Netherlands"
        }
        }
        ]
        }
        ]
        },
        </xsl:if>
        "socialscience": {
        "displayName": "Social Science and Humanities Metadata",
        "name": "socialscience",
        "fields": [
        {
        "typeName": "collectionMode",
        "multiple": true,
        "typeClass": "primitive",
	"value": [
	<xsl:for-each select="//ns1:subject[@subjectScheme='CID collection mode']">
                "<xsl:value-of select="."/>"
		<xsl:if test="position() != last()">
			<xsl:text>,</xsl:text>
		</xsl:if>
	</xsl:for-each>
        ]
	}
        ]
        }
        }
        }

        }

    </xsl:template>

    <!-- template to output a number value -->


</xsl:stylesheet>
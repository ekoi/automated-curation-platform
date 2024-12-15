<?xml version="1.0"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:math="http://www.w3.org/2005/xpath-functions/math"
    xmlns:xs="http://www.w3.org/2001/XMLSchema" exclude-result-prefixes="xs math" version="3.0">
    <xsl:output indent="yes" omit-xml-declaration="yes"/>
    <xsl:template match="data">
        <!-- create a new root tag -->
        <!-- apply the xml structure generated from JSON -->
        <xsl:apply-templates select="json-to-xml(.)"/>
    </xsl:template>
    <!-- template for the         first tag -->
    <xsl:template match="/map" xpath-default-namespace="http://www.w3.org/2005/xpath-functions"> {
        "datasetVersion":
            {
                "license":
                    {
                    "name": "CC0 1.0", "uri": "http://creativecommons.org/publicdomain/zero/1.0"
                    },
                "metadataBlocks": {
                    "citation": {
                        "fields": [
                            {
                                "value": "<xsl:value-of select="//array[@key = 'metadata']/map/string[@key = 'id' and text() = 'citation_metadata']/following-sibling::array[@key = 'fields']/map/string[@key = 'name' and text() = 'title']/following-sibling::string[@key = 'value']/."/>"
                                "typeClass": "primitive",
                                "multiple": false,
                                "typeName": "title"
                            },
                            {
                                "value": [
                                    {
                                        "authorName": {
                                            "value": "<xsl:value-of select="//array[@key = 'metadata']/map/string[@key = 'id' and text() = 'citation_metadata']/following-sibling::array[@key = 'fields']/map/string[@key = 'name' and text() = 'author']/following-sibling::string[@key = 'value']"/>",
                                            "typeClass": "primitive",
                                            "multiple": false,
                                            "typeName": "authorName"
                                        }
                                    }
                                        <xsl:for-each   select="//array[@key = 'metadata']/map/string[@key = 'id' and text() = 'citation_metadata']/following-sibling::array[@key = 'fields']/map/string[@key = 'name' and text() = 'additional_authors']/following-sibling::array[@key = 'fields']/array">
                                            <xsl:if test="map/string[@key = 'name' and text() = 'additional_author_type']/following-sibling::map[@key = 'value']/string[@key = 'value' and text() = 'Dataset author']">
                                                ,
                                                {
                                                    "authorName": {
                                                        "typeName": "authorName",
                                                        "multiple": false,
                                                        "typeClass": "primitive",
                                                        "value": "<xsl:value-of select="map/string[@key = 'name' and text() = 'additional_author']/following-sibling::string[@key = 'value']"/>"
                                                    },
                                                    "authorAffiliation": {
                                                        "typeName": "authorAffiliation",
                                                        "multiple": false,
                                                        "typeClass": "primitive",
                                                        "value": "<xsl:value-of select="map/string[@key = 'name' and text() = 'additional_author_type']/following-sibling::map[@key = 'value']/string[@key = 'value']"/>"
                                                    }
                                                }
                                            </xsl:if>
                                        </xsl:for-each>
                                ],
                                "typeClass": "compound",
                                "multiple": true,
                                "typeName": "author"
                            },
                            {
                                "typeName": "dataSources",
                                "multiple": true,
                                "typeClass": "primitive",
                                "value": ["<xsl:value-of select="//string[@key = 'swh-staging-api']/."/>" ]
                            },
                            {
                                "value": [
                                    {
                                        "datasetContactEmail" :
                                            {
                                                "typeClass": "primitive",
                                                "multiple": false, "typeName": "datasetContactEmail",
                                                "value" : "<xsl:value-of select="//array[@key = 'metadata']/map/string[@key = 'id' and text() = 'citation_metadata']/following-sibling::array[@key = 'fields']/map/string[@key = 'name' and text() = 'contact_email']/following-sibling::string[@key = 'value']"/>"
                                            }
                                    }
                                ],
                                "typeClass": "compound",
                                "multiple": true,
                                "typeName": "datasetContact"
                            },
                            {
                                "value": [
                                    {
                                        "dsDescriptionValue":
                                            {
                                                "value": "<xsl:value-of select="//array[@key = 'metadata']/map/string[@key = 'id' and text() = 'citation_metadata']/following-sibling::array[@key = 'fields']/map/string[@key = 'name' and text() = 'description']/following-sibling::string[@key = 'value']"/>",
                                                "multiple":false,
                                                "typeClass": "primitive",
                                                "typeName": "dsDescriptionValue"
                                            }
                                    }
                                ],
                                "typeClass": "compound",
                                "multiple": true,
                                "typeName": "dsDescription"
                            },
                            {
                                "value": [ "<xsl:value-of select="//array[@key = 'metadata']/map/string[@key = 'id' and text() = 'citation_metadata']/following-sibling::array[@key = 'fields']/map/string[@key = 'name' and text() = 'subject']/following-sibling::map[@key = 'value']/string[@key = 'value']"/>" ],
                                "typeClass": "controlledVocabulary",
                                "multiple": true,
                                "typeName": "subject"
                            }
                        ],
                        "displayName": "Citation Metadata"
                    }
                }
            }
        }
    </xsl:template>
    <!-- template to output a number         value -->
</xsl:stylesheet>

"""
Result models for the BDA optimization application.
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import pandas as pd
import os
import json


class BoundingBox(BaseModel):
    """
    Represents a bounding box in a document.
    """
    left: float
    top: float
    width: float
    height: float


class Geometry(BaseModel):
    """
    Represents geometry information for a field.
    """
    page: int
    boundingBox: Optional[BoundingBox] = None


class FieldExplainability(BaseModel):
    """
    Represents explainability information for a field.
    """
    confidence: float
    geometry: List[Geometry] = Field(default_factory=list)


class BDAResult(BaseModel):
    """
    Represents the result of a BDA job.
    """
    field_name: str
    value: str
    confidence: Optional[float] = None
    page: Optional[int] = None
    bounding_box: Optional[str] = None

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> List["BDAResult"]:
        """
        Create BDA results from a DataFrame.
        
        Args:
            df: DataFrame with BDA results
            
        Returns:
            List[BDAResult]: List of BDA results
        """
        results = []
        for _, row in df.iterrows():
            results.append(cls(
                field_name=row["field_name"],
                value=row["value"],
                confidence=row.get("confidence"),
                page=row.get("page"),
                bounding_box=row.get("bounding_box")
            ))
        return results


class BDAResponse(BaseModel):
    """
    Represents the response from a BDA job.
    """
    inference_result: Dict[str, str]
    explainability_info: List[Dict[str, FieldExplainability]]
    document_class: Dict[str, str]

    @classmethod
    def from_s3(cls, s3_uri: str) -> "BDAResponse":
        """
        Create a BDA response from an S3 URI.
        
        Args:
            s3_uri: S3 URI of the JSON file
            
        Returns:
            BDAResponse: BDA response
        """
        from src.util import read_s3_object
        json_data = json.loads(read_s3_object(s3_uri))
        return cls(**json_data)
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert BDA response to a DataFrame.
        
        Returns:
            pd.DataFrame: DataFrame with BDA results
        """
        records = []
        for field, value in self.inference_result.items():
            info = self.explainability_info[0].get(field, {})
            confidence = round(info.confidence, 4) if hasattr(info, 'confidence') else None

            geometry = info.geometry if hasattr(info, 'geometry') else []
            page = geometry[0].page if geometry else None
            bbox = geometry[0].boundingBox if geometry and hasattr(geometry[0], 'boundingBox') else None

            records.append({
                "field_name": field,
                "value": value,
                "confidence": confidence,
                "page": page,
                "bounding_box": json.dumps(bbox.model_dump()) if bbox else None
            })

        return pd.DataFrame(records)
    
    def save_to_csv(self, output_path: str) -> str:
        """
        Save BDA response to a CSV file.
        
        Args:
            output_path: Path to save the CSV file
            
        Returns:
            str: Path to the saved CSV file
        """
        try:
            df = self.to_dataframe()
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            df.to_csv(output_path, index=False)
            print(f"✅ BDA results saved to {output_path}")
            return output_path
        except Exception as e:
            print(f"❌ Error saving BDA results: {e}")
            return ""
    
    def save_to_html(self, output_path: str) -> str:
        """
        Save BDA response to an HTML file.
        
        Args:
            output_path: Path to save the HTML file
            
        Returns:
            str: Path to the saved HTML file
        """
        try:
            df = self.to_dataframe()
            
            # Extract document class
            document_class = self.document_class.get("type", "N/A")
            
            # Convert DataFrame to HTML table
            table_html = df.to_html(index=False, escape=False)
            
            # HTML template
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Document Analysis</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        padding: 20px;
                        background-color: #f9f9f9;
                    }}
                    h2 {{
                        color: #2c3e50;
                    }}
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin-top: 20px;
                    }}
                    th, td {{
                        border: 1px solid #ccc;
                        padding: 10px;
                        text-align: left;
                    }}
                    th {{
                        background-color: #4CAF50;
                        color: white;
                    }}
                    tr:nth-child(even) {{
                        background-color: #f2f2f2;
                    }}
                    .document-class {{
                        font-size: 18px;
                        font-weight: bold;
                        margin-bottom: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="document-class">Document Class: {document_class}</div>
                {table_html}
            </body>
            </html>
            """
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ HTML saved to {output_path}")
            return output_path
        except Exception as e:
            print(f"❌ Error saving HTML: {e}")
            return ""


class MergedResult(BaseModel):
    """
    Represents a merged result of BDA and input data.
    """
    field: str
    instruction: str
    value: str
    confidence: Optional[float] = None
    expected_output: str
    data_in_document: bool
    semantic_similarity: Optional[float] = None
    semantic_match: Optional[bool] = None

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> List["MergedResult"]:
        """
        Create merged results from a DataFrame.
        
        Args:
            df: DataFrame with merged results
            
        Returns:
            List[MergedResult]: List of merged results
        """
        results = []
        for _, row in df.iterrows():
            results.append(cls(
                field=row["Field"],
                instruction=row["Instruction"],
                value=row["Value (BDA Response)"],
                confidence=row.get("Confidence"),
                expected_output=row["Expected Output"],
                data_in_document=row["Data in Document"],
                semantic_similarity=row.get("semantic_similarity"),
                semantic_match=row.get("semantic_match")
            ))
        return results

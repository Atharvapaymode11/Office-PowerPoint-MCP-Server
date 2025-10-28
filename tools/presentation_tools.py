"""
Presentation management tools for PowerPoint MCP Server.
Handles presentation creation, opening, saving, and core properties.
Now includes S3 storage support.
"""
from typing import Dict, List, Optional, Any
import os
import logging
from mcp.server.fastmcp import FastMCP
import utils as ppt_utils
from utils.s3_utils import get_s3_handler

# Configure logging
logger = logging.getLogger(__name__)


def register_presentation_tools(app: FastMCP, presentations: Dict, get_current_presentation_id, get_template_search_directories):
    """Register presentation management tools with the FastMCP app"""
    
    @app.tool()
    def create_presentation(id: Optional[str] = None) -> Dict:
        """Create a new PowerPoint presentation."""
        # Create a new presentation
        pres = ppt_utils.create_presentation()
        
        # Generate an ID if not provided
        if id is None:
            id = f"presentation_{len(presentations) + 1}"
        
        # Store the presentation
        presentations[id] = pres
        # Set as current presentation (this would need to be handled by caller)
        
        return {
            "presentation_id": id,
            "message": f"Created new presentation with ID: {id}",
            "slide_count": len(pres.slides)
        }

    @app.tool()
    def create_presentation_from_template(template_path: str, id: Optional[str] = None) -> Dict:
        """Create a new PowerPoint presentation from a template file."""
        # Check if template file exists
        if not os.path.exists(template_path):
            # Try to find the template by searching in configured directories
            search_dirs = get_template_search_directories()
            template_name = os.path.basename(template_path)
            
            for directory in search_dirs:
                potential_path = os.path.join(directory, template_name)
                if os.path.exists(potential_path):
                    template_path = potential_path
                    break
            else:
                env_path_info = f" (PPT_TEMPLATE_PATH: {os.environ.get('PPT_TEMPLATE_PATH', 'not set')})" if os.environ.get('PPT_TEMPLATE_PATH') else ""
                return {
                    "error": f"Template file not found: {template_path}. Searched in {', '.join(search_dirs)}{env_path_info}"
                }
        
        # Create presentation from template
        try:
            pres = ppt_utils.create_presentation_from_template(template_path)
        except Exception as e:
            return {
                "error": f"Failed to create presentation from template: {str(e)}"
            }
        
        # Generate an ID if not provided
        if id is None:
            id = f"presentation_{len(presentations) + 1}"
        
        # Store the presentation
        presentations[id] = pres
        
        return {
            "presentation_id": id,
            "message": f"Created new presentation from template '{template_path}' with ID: {id}",
            "template_path": template_path,
            "slide_count": len(pres.slides),
            "layout_count": len(pres.slide_layouts)
        }

    @app.tool()
    def open_presentation(file_path: str, id: Optional[str] = None) -> Dict:
        """Open an existing PowerPoint presentation from a file."""
        # Check if file exists
        if not os.path.exists(file_path):
            return {
                "error": f"File not found: {file_path}"
            }
        
        # Open the presentation
        try:
            pres = ppt_utils.open_presentation(file_path)
        except Exception as e:
            return {
                "error": f"Failed to open presentation: {str(e)}"
            }
        
        # Generate an ID if not provided
        if id is None:
            id = f"presentation_{len(presentations) + 1}"
        
        # Store the presentation
        presentations[id] = pres
        
        return {
            "presentation_id": id,
            "message": f"Opened presentation from {file_path} with ID: {id}",
            "slide_count": len(pres.slides)
        }

    @app.tool()
    def save_presentation(file_path: str, presentation_id: Optional[str] = None) -> Dict:
        """
        Save a presentation to a file or S3 bucket.
        
        Behavior:
        - If S3_ENABLED=true: Uploads to S3 and returns S3 URLs
        - If S3_ENABLED=false: Saves to local file system
        
        Args:
            file_path: File path/name to save the presentation
            presentation_id: Presentation ID (uses current if not specified)
        
        Returns:
            Dict with save results including S3 info if applicable
        """
        # Use the specified presentation or the current one
        pres_id = presentation_id if presentation_id is not None else get_current_presentation_id()
        
        if pres_id is None or pres_id not in presentations:
            return {
                "success": False,
                "error": "No presentation is currently loaded or the specified ID is invalid"
            }
        
        pres = presentations[pres_id]
        
        try:
            # Get S3 handler to check if S3 is enabled
            s3_handler = get_s3_handler()
            
            if s3_handler.s3_enabled:
                # S3 MODE: Upload to S3
                logger.info(f"S3 mode enabled - uploading presentation to S3")
                
                # Extract filename from path (ignore directory structure)
                filename = os.path.basename(file_path)
                
                # Upload to S3
                result = s3_handler.upload_presentation(pres, filename)
                
                if result["success"]:
                    # Generate presigned URL for temporary access (1 hour)
                    presigned_url = s3_handler.generate_presigned_url(
                        result["key"], 
                        expiration=3600
                    )
                    
                    response = {
                        "success": True,
                        "message": f"Presentation saved to S3: {result['s3_url']}",
                        "storage_type": "s3",
                        "s3_url": result["s3_url"],
                        "https_url": result["https_url"],
                        "bucket": result["bucket"],
                        "key": result["key"],
                        "filename": result["filename"],
                        "presentation_id": pres_id
                    }
                    
                    if presigned_url:
                        response["presigned_url"] = presigned_url
                        response["presigned_url_expires"] = "1 hour"
                        response["message"] += f"\n\nTemporary download URL (expires in 1 hour):\n{presigned_url}"
                    
                    logger.info(f"Successfully uploaded {filename} to S3")
                    return response
                else:
                    # S3 upload failed
                    logger.error(f"S3 upload failed: {result.get('error', 'Unknown error')}")
                    return {
                        "success": False,
                        "storage_type": "s3",
                        "error": result.get("error", "Failed to upload to S3")
                    }
            
            else:
                # LOCAL MODE: Save to local file system
                logger.info(f"Local mode - saving presentation to {file_path}")
                
                saved_path = ppt_utils.save_presentation(pres, file_path)
                
                return {
                    "success": True,
                    "message": f"Presentation saved to local file: {saved_path}",
                    "storage_type": "local",
                    "file_path": saved_path,
                    "presentation_id": pres_id
                }
        
        except ValueError as e:
            # Configuration error (e.g., S3 enabled but credentials missing)
            logger.error(f"Configuration error: {str(e)}")
            return {
                "success": False,
                "error": f"Configuration error: {str(e)}. Please check your S3 environment variables."
            }
        
        except Exception as e:
            # Generic error
            logger.error(f"Failed to save presentation: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to save presentation: {str(e)}"
            }

    @app.tool()
    def get_presentation_info(presentation_id: Optional[str] = None) -> Dict:
        """Get information about a presentation."""
        pres_id = presentation_id if presentation_id is not None else get_current_presentation_id()
        
        if pres_id is None or pres_id not in presentations:
            return {
                "error": "No presentation is currently loaded or the specified ID is invalid"
            }
        
        pres = presentations[pres_id]
        
        try:
            info = ppt_utils.get_presentation_info(pres)
            info["presentation_id"] = pres_id
            return info
        except Exception as e:
            return {
                "error": f"Failed to get presentation info: {str(e)}"
            }

    @app.tool()
    def get_template_file_info(template_path: str) -> Dict:
        """Get information about a template file including layouts and properties."""
        # Check if template file exists
        if not os.path.exists(template_path):
            # Try to find the template by searching in configured directories
            search_dirs = get_template_search_directories()
            template_name = os.path.basename(template_path)
            
            for directory in search_dirs:
                potential_path = os.path.join(directory, template_name)
                if os.path.exists(potential_path):
                    template_path = potential_path
                    break
            else:
                return {
                    "error": f"Template file not found: {template_path}. Searched in {', '.join(search_dirs)}"
                }
        
        try:
            return ppt_utils.get_template_info(template_path)
        except Exception as e:
            return {
                "error": f"Failed to get template info: {str(e)}"
            }

    @app.tool()
    def set_core_properties(
        title: Optional[str] = None,
        subject: Optional[str] = None,
        author: Optional[str] = None,
        keywords: Optional[str] = None,
        comments: Optional[str] = None,
        presentation_id: Optional[str] = None
    ) -> Dict:
        """Set core document properties."""
        pres_id = presentation_id if presentation_id is not None else get_current_presentation_id()
        
        if pres_id is None or pres_id not in presentations:
            return {
                "error": "No presentation is currently loaded or the specified ID is invalid"
            }
        
        pres = presentations[pres_id]
        
        try:
            ppt_utils.set_core_properties(
                pres,
                title=title,
                subject=subject,
                author=author,
                keywords=keywords,
                comments=comments
            )
            
            return {
                "success": True,
                "message": "Core properties updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to set core properties: {str(e)}"
            }
    
    @app.tool()
    def get_storage_mode() -> Dict:
        """
        Get current storage mode configuration (S3 or local).
        Useful for debugging and understanding current setup.
        """
        try:
            s3_handler = get_s3_handler()
            
            if s3_handler.s3_enabled:
                return {
                    "success": True,
                    "storage_mode": "s3",
                    "s3_bucket": s3_handler.s3_bucket,
                    "s3_prefix": s3_handler.s3_prefix,
                    "s3_region": s3_handler.s3_region,
                    "message": "S3 storage is ENABLED - presentations will be saved to S3"
                }
            else:
                return {
                    "success": True,
                    "storage_mode": "local",
                    "message": "Local storage is active - presentations will be saved to local file system"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get storage mode: {str(e)}"
            }
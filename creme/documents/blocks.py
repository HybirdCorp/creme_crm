import warnings

from .bricks import (
    FolderDocsBrick as FolderDocsBlock,
    ChildFoldersBrick as ChildFoldersBlock,
    LinkedDocsBrick as LinkedDocsBlock,
)

warnings.warn('documents.blocks is deprecated ; use documents.bricks instead.', DeprecationWarning)

folder_docs_block   = FolderDocsBlock()
child_folders_block = ChildFoldersBlock()
linked_docs_block   = LinkedDocsBlock()

import asyncio
import json
import logging
import pathlib
import watchgod  # type: ignore
import zipfile

from typing import List, Optional, Tuple

from dsw_tdk.api_client import DSWAPIClient, DSWCommunicationError
from dsw_tdk.consts import DEFAULT_ENCODING
from dsw_tdk.model import TemplateProject, Template, TemplateFile, TemplateFileType
from dsw_tdk.utils import UUIDGen
from dsw_tdk.validation import ValidationError, TemplateValidator


ChangeItem = Tuple[watchgod.Change, pathlib.Path]


class TDKCore:

    def __init__(self, template: Optional[Template] = None, project: Optional[TemplateProject] = None,
                 client: Optional[DSWAPIClient] = None, logger: Optional[logging.Logger] = None):
        self.template = template
        self.project = project
        self.client = client
        self.logger = logger or logging.getLogger()
        self.loop = asyncio.get_event_loop()
        self.changes_processor = ChangesProcessor(self)

    @property
    def safe_template(self) -> Template:
        if self.template is None:
            raise RuntimeError('No template is loaded')
        return self.template

    @property
    def safe_project(self) -> TemplateProject:
        if self.project is None:
            raise RuntimeError('No template is loaded')
        return self.project

    @property
    def safe_client(self) -> DSWAPIClient:
        if self.client is None:
            raise RuntimeError('No DSW API client specified')
        return self.client

    async def init_client(self, api_url: str, username: str, password: str):
        self.logger.info(f'Connecting to {api_url}')
        self.client = DSWAPIClient(api_url=api_url)
        await self.client.login(email=username, password=password)
        self.logger.info(f'Successfully authenticated as {username}')

    def prepare_local(self, template_dir):
        self.logger.debug('Preparing local template project')
        self.project = TemplateProject(template_dir=template_dir, logger=self.logger)

    def load_local(self, template_dir):
        self.prepare_local(template_dir=template_dir)
        self.logger.info('Loading local template project')
        self.project.load()

    async def load_remote(self, template_id: str):
        self.logger.info(f'Retrieving template {template_id}')
        self.template = await self.safe_client.get_template(template_id=template_id)
        self.logger.debug('Retrieving template files')
        files = await self.safe_client.get_template_files(template_id=template_id)
        self.logger.info(f'Retrieved {len(files)} file(s)')
        for tfile in files:
            self.safe_template.files[tfile.filename.as_posix()] = tfile
        self.logger.debug('Retrieving template assets')
        assets = await self.safe_client.get_template_assets(template_id=template_id)
        self.logger.info(f'Retrieved {len(assets)} asset(s)')
        for tfile in assets:
            self.safe_template.files[tfile.filename.as_posix()] = tfile

    async def list_remote(self) -> List[Template]:
        self.logger.info('Listing remote templates')
        return await self.safe_client.get_templates()

    def verify(self) -> List[ValidationError]:
        template = self.template or self.safe_project.template
        if template is None:
            raise RuntimeError('No template is loaded')
        return TemplateValidator.collect_errors(template)

    def store_local(self, force: bool):
        if self.project is None:
            raise RuntimeError('No template project is initialized')
        self.project.template = self.safe_template
        self.logger.debug(f'Initiating storing local template project (force={force})')
        self.project.store(force=force)

    async def store_remote(self, force: bool):
        self.template = self.safe_project.template
        template_id = self.safe_template.id
        template_exists = await self.safe_client.check_template_exists(template_id=template_id)
        if template_exists and force:
            self.logger.warning('Deleting existing remote template (forced)')
            result = await self.safe_client.delete_template(template_id=template_id)
            if not result:
                self.logger.error('Could not delete template (used by some documents?)')
            template_exists = not result

        if template_exists:
            self.logger.info('Updating existing remote template')
            await self.safe_client.put_template(template=self.safe_template)
            self.logger.debug('Retrieving remote assets')
            remote_assets = await self.safe_client.get_template_assets(template_id=self.safe_template.id)
            self.logger.debug('Retrieving remote files')
            remote_files = await self.safe_client.get_template_files(template_id=self.safe_template.id)
            await self.cleanup_remote_files(remote_assets=remote_assets, remote_files=remote_files)
        else:
            self.logger.info('Creating remote template')
            await self.safe_client.post_template(template=self.safe_template)
        await self.store_remote_files()

    async def _delete_template_file(self, tfile: TemplateFile, project_update: bool = False):
        try:
            self.logger.debug(f'Deleting existing remote {tfile.remote_type.value} '
                              f'{tfile.filename.as_posix()} ({tfile.remote_id})')
            if tfile.remote_type == TemplateFileType.asset:
                result = await self.safe_client.delete_template_asset(template_id=self.safe_template.id, asset_id=tfile.remote_id)
            else:
                result = await self.safe_client.delete_template_file(template_id=self.safe_template.id, file_id=tfile.remote_id)
            self.logger.debug(f'Deleting existing remote {tfile.remote_type.value} '
                              f'{tfile.filename.as_posix()} ({tfile.remote_id}): {result}')
            if project_update and result:
                self.safe_project.remove_template_file(tfile.filename)
        except Exception as e:
            self.logger.error(f'Failed to delete existing remote {tfile.remote_type.value} '
                              f'{tfile.filename.as_posix()}: {e}')

    async def cleanup_remote_files(self, remote_assets: List[TemplateFile], remote_files: List[TemplateFile]):
        futures = []
        for tfile in self.safe_project.safe_template.files.values():
            self.logger.debug(f'Cleaning up remote {tfile.filename.as_posix()}')
            for remote_asset in remote_assets:
                if remote_asset.filename == tfile.filename:
                    futures.append(asyncio.ensure_future(
                        self._delete_template_file(tfile=remote_asset, project_update=False)
                    ))
            for remote_file in remote_files:
                if remote_file.filename == tfile.filename:
                    futures.append(asyncio.ensure_future(
                        self._delete_template_file(tfile=remote_file, project_update=False)
                    ))
        await asyncio.gather(*futures)

    async def _create_template_file(self, tfile: TemplateFile, project_update: bool = False):
        try:
            self.logger.debug(f'Storing remote {tfile.remote_type.value} {tfile.filename.as_posix()} ({tfile.remote_id})')
            if tfile.remote_type == TemplateFileType.asset:
                result = await self.safe_client.post_template_asset(template_id=self.safe_template.id, tfile=tfile)
            else:
                result = await self.safe_client.post_template_file(template_id=self.safe_template.id, tfile=tfile)
            self.logger.debug(f'Storing remote {tfile.remote_type.value} {tfile.filename.as_posix()} '
                              f'({tfile.remote_id}): {result.remote_id}')
            if project_update and result is not None:
                self.safe_project.update_template_file(result)
        except Exception as e:
            self.logger.error(f'Failed to store remote {tfile.remote_type.value} {tfile.filename.as_posix()}: {e}')

    async def store_remote_files(self):
        futures = []
        for tfile in self.safe_project.template.files.values():
            tfile.remote_id = None
            tfile.remote_type = TemplateFileType.file if tfile.is_text else TemplateFileType.asset
            futures.append(asyncio.ensure_future(
                self._create_template_file(tfile=tfile, project_update=True)
            ))
        await asyncio.gather(*futures)

    def create_package(self, output: pathlib.Path, force: bool):
        if output.exists() and not force:
            raise RuntimeError(f'File {output} already exists (not forced)')
        self.logger.debug(f'Opening ZIP file for write: {output}')
        package = zipfile.ZipFile(output, mode='w', compression=zipfile.ZIP_DEFLATED)
        descriptor = self.safe_project.safe_template.serialize_remote()
        files = []
        assets = []
        for tfile in self.safe_project.safe_template.files.values():
            if tfile.is_text:
                self.logger.info(f'Adding template file {tfile.filename.as_posix()}')
                files.append({
                    'uuid': str(UUIDGen.generate()),
                    'content': tfile.content.decode(encoding=DEFAULT_ENCODING),
                    'fileName': str(tfile.filename.as_posix()),
                })
            else:
                self.logger.info(f'Adding template asset {tfile.filename.as_posix()}')
                assets.append({
                    'uuid': str(UUIDGen.generate()),
                    'contentType': tfile.content_type,
                    'fileName': str(tfile.filename.as_posix()),
                })
                self.logger.debug(f'Packaging template asset {tfile.filename}')
                package.writestr(str('template/assets/' + tfile.filename.as_posix()), tfile.content)
        descriptor['files'] = files
        descriptor['assets'] = assets
        self.logger.debug('Packaging template.json file')
        package.writestr('template/template.json', data=json.dumps(descriptor, indent=4))
        self.logger.debug('Closing ZIP package')
        package.close()
        self.logger.debug('ZIP packaging done')

    async def watch_project(self, callback):
        async for changes in watchgod.awatch(self.safe_project.template_dir):
            await callback((
                change for change in ((change[0], pathlib.Path(change[1])) for change in changes)
                if self.safe_project.is_template_file(
                    change[1], include_descriptor=True, include_readme=True
                )
            ))

    async def _update_descriptor(self):
        try:
            template_exists = await self.client.check_template_exists(template_id=self.safe_project.template.id)
            if template_exists:
                self.logger.info(f'Updating existing remote template {self.project.template.id}')
                await self.client.put_template(template=self.project.template)
            else:
                # TODO: optimization - reload full template and send it, skip all other changes
                self.logger.info(f'Template {self.safe_project.template.id} does not exist on remote - full sync')
                await self.store_remote(force=False)
        except DSWCommunicationError as e:
            self.logger.error(f'Failed to update template {self.safe_project.safe_template.id}: {e.message}')
        except Exception as e:
            self.logger.error(f'Failed to update template {self.safe_project.safe_template.id}: {e}')

    async def _delete_file(self, filepath: pathlib.Path):
        try:
            tfile = self.safe_project.get_template_file(filepath=filepath)
            if tfile is None:
                # TODO: try to check if exists on remote (may not be synced yet)
                self.logger.info(f'File {filepath.as_posix()} not tracked currently - skipping')
                return
            await self._delete_template_file(tfile=tfile, project_update=True)
        except Exception as e:
            self.logger.error(f'Failed to delete file {filepath.as_posix()}: {e}')

    async def _update_file(self, filepath: pathlib.Path):
        # TODO: optimization - use PUT if possible
        try:
            tfile = self.safe_project.get_template_file(filepath=filepath)
            if tfile is not None:
                await self._delete_template_file(tfile=tfile)
            tfile = self.safe_project.load_file(filepath=filepath)
            await self._create_template_file(tfile=tfile, project_update=True)
        except Exception as e:
            self.logger.error(f'Failed to update file {filepath.as_posix()}: {e}')

    async def process_changes(self, changes: List[ChangeItem], force: bool):
        self.changes_processor.clear()
        try:
            await self.changes_processor.process_changes(changes, force)
        except Exception as e:
            self.logger.error(f'Failed to process changes: {e}')


class ChangesProcessor:

    def __init__(self, tdk: TDKCore):
        self.tdk = tdk  # type: TDKCore
        self.descriptor_change = None  # type: Optional[ChangeItem]
        self.readme_change = None  # type: Optional[ChangeItem]
        self.file_changes = []  # type: List[ChangeItem]

    def clear(self):
        self.descriptor_change = None
        self.readme_change = None
        self.file_changes = []

    def _split_changes(self, changes: List[ChangeItem]):
        for change in changes:
            if change[1] == self.tdk.safe_project.descriptor_path:
                self.descriptor_change = change
            elif change[1] == self.tdk.safe_project.used_readme:
                self.readme_change = change
            elif self.tdk.safe_project.is_template_file(change[1]):
                self.file_changes.append(change)

    async def _process_file_changes(self):
        futures = []
        deleted = set()
        updated = set()
        for file_change in self.file_changes:
            self.tdk.logger.debug(f'Processing {file_change}')
            change_type = file_change[0]
            filepath = file_change[1]
            if change_type == watchgod.Change.deleted and filepath not in deleted:
                self.tdk.logger.debug('Scheduling delete operation')
                deleted.add(filepath)
                futures.append(asyncio.ensure_future(self.tdk._delete_file(filepath)))
            elif filepath not in updated:
                self.tdk.logger.debug('Scheduling update operation')
                updated.add(filepath)
                futures.append(asyncio.ensure_future(self.tdk._update_file(filepath)))
        await asyncio.gather(*futures)

    async def _reload_descriptor(self, force: bool) -> bool:
        if self.descriptor_change is None:
            return False
        if self.descriptor_change[0] == watchgod.Change.deleted:
            raise RuntimeError(f'Deleted template descriptor {self.tdk.safe_project.descriptor_path} ... the end')
        self.tdk.logger.debug(f'Reloading {TemplateProject.TEMPLATE_FILE} file')
        previous_id = self.tdk.safe_project.safe_template.id
        self.tdk.safe_project.load_descriptor()
        self.tdk.safe_project.load_readme()
        new_id = self.tdk.safe_project.safe_template.id
        if new_id != previous_id:
            self.tdk.logger.warning(f'Template ID changed from {previous_id} to {new_id}')
            self.tdk.safe_project.load()
            await self.tdk.store_remote(force=force)
            self.tdk.logger.info('Template fully reloaded... waiting for new changes')
            return True
        return False

    async def _reload_readme(self) -> bool:
        if self.readme_change is None:
            return False
        if self.readme_change[0] == watchgod.Change.deleted:
            raise RuntimeError(f'Deleted used README file {self.tdk.safe_project.used_readme}')
        self.tdk.logger.debug('Reloading README file')
        self.tdk.safe_project.load_readme()
        return True

    async def _update_descriptor(self):
        if self.readme_change is not None or self.descriptor_change is not None:
            self.tdk.logger.debug('Updating template descriptor (metadata)')
            await self.tdk._update_descriptor()

    async def process_changes(self, changes: List[ChangeItem], force: bool):
        self._split_changes(changes)
        full_reload = await self._reload_descriptor(force)
        if not full_reload:
            await self._reload_readme()
            await self._update_descriptor()
            await self._process_file_changes()
        self.tdk.logger.info('All changes processed... waiting for new changes')

# GitHub packages cleaner-up'er

  

Ideally your pipelines and automations should auto cleanup artifacts/packages after development is done but in case you live in the real world, here's a little cleanup script for you.

Word of caution:  If you have packages built from another package in your organization, ensure you are not deleting the version another package was built from.  A package could have an untagged version in it's layers and deleting that version will render the package unpullable.

## Config options

  

### `[gh]`

`token` - A GH PAT with access to the organization and `read:packages`,`delete:packages` permissions
`org_name` - Name of your GH Organization to crawl.
`url` - API endpoint of GH's API. Shouldn't need to be changed

### `[package]`
 `last_updated` - Integer number of days ago a package's version was last updated.
 `type` - A comma separated list of package types to look for.  
	 Allowable values are: `npm`,`maven`,`rubygems`,`docker`,`nuget`,`container` or `all`

### `[global]`
`delete_untagged` - Possbile values: `all`, `only`, `normal`
  - `all` - Script will delete ALL untagged package versions it finds regardless of `last_updated` criteria
  - `only` - Script will ONLY delete untagged package versions it finds regardless of `last_updated` criteria
  - `normal` - No special treatment of untagged package versions.  `last_updated` criteria will be applied
  - `none` - Do not delete any untagged package versions found
 
`unattended` - Script will prompt for confirmation before deletion, set this to `true` to auto-accept the prompt.

### `[filters]`
Only cleanup up package versions that match the below criteria expressed using regex
(Uses python re module)
`package_name_match_pattern` - Regex pattern to match which packages to consider
`repository_name_match_pattern` - Regex pattern to match which repositories to look in
`package_tag_match_pattern` - Regex pattern to match which packages tags to consider (Untagged package versions will be considered independently of any regex supplied here)

## Usage
Once your `config.ini` file is updated with your options, execute via CLI with:
`python3 prune_gh_packages.py`

## Notes
GH API does not have a batch deletion option so there will be 1 API call made per version deleted.  Be mindful of your GH rate limits (rate limit usage will be output in the script)

## Future enhancements
- Leverage multiprocessing to delete package versions faster
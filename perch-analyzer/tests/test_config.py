import tempfile
from perch_analyzer.config import config


def test_config_write_load():
    with tempfile.NamedTemporaryFile() as temp:
        conf = config.Config(
            config_path=temp.name, project_name="test", user_name="birder"
        )

        conf.to_file()

        conf_loaded = config.Config.load(temp.name)

        assert conf == conf_loaded

"""Content Engine Orchestrator for sequence-to-video integration."""

from domains.content.core.llm_client import LLMClient
from domains.content.domain.schema_input import UserRequest
from domains.content.domain.schema_output import FinalContentPlan
from domains.content.modules.mod_01_generate_queries import QueryEngine
from domains.content.modules.mod_02_fetcher import DataFetcher
from domains.content.modules.mod_03_xml_tagger import XmlTagger
from domains.content.modules.mod_04_skeleton_selector import SkeletonSelector
from domains.content.modules.mod_05_script_assembler import ScriptAssembler
from domains.content.modules.mod_06_script_polisher import ScriptPolisher
from domains.content.modules.mod_07_direction_injector import DirectionInjector
from domains.content.modules.mod_08_visual_outlay import VisualOutlayGenerator


class ContentEngineOrchestrator:
    """Orchestrates the complete content generation pipeline."""

    def __init__(self):
        """Initialize orchestrator with all module dependencies."""
        # Initialize LLM client (shared across modules)
        self.llm_client = LLMClient()

        # Initialize all modules with dependency injection
        self.query_engine = QueryEngine(llm_client=self.llm_client)
        self.data_fetcher = DataFetcher(llm_client=self.llm_client)
        self.xml_tagger = XmlTagger(llm_client=self.llm_client)
        self.skeleton_selector = SkeletonSelector(llm_client=self.llm_client)
        self.script_assembler = ScriptAssembler(llm_client=self.llm_client)
        self.script_polisher = ScriptPolisher(llm_client=self.llm_client)
        self.direction_injector = DirectionInjector(llm_client=self.llm_client)
        self.visual_outlay_generator = VisualOutlayGenerator(llm_client=self.llm_client)

    async def generate_content_plan(self, user_request: UserRequest) -> FinalContentPlan:
        """
        Generate complete content plan from user request.

        Pipeline steps:
        1. Generate search queries
        2. Fetch data from YouTube, Google Search
        3. Tag transcripts with XML tags
        4. Select appropriate skeleton pattern
        5. Assemble draft script
        6. Polish script
        7. Inject directing instructions
        8. Generate visual outlay

        Args:
            user_request: User request with topic and persona

        Returns:
            FinalContentPlan with polished script, directions, and visual outlay
        """
        # Step 1: Generate search queries
        search_queries = await self.query_engine.generate_queries(user_request)

        # Step 2: Fetch data
        content_material = await self.data_fetcher.fetch_content_material(search_queries)

        # Step 3: Tag transcripts with XML tags
        tagged_transcripts = await self.xml_tagger.tag_multiple_transcripts(
            content_material.transcripts
        )

        # Step 4: Select skeleton pattern
        skeleton_pattern = await self.skeleton_selector.select_skeleton_pattern(
            tagged_transcripts=tagged_transcripts,
            topic=user_request.topic
        )

        # Step 5: Assemble draft script
        draft_script = await self.script_assembler.assemble_script(
            skeleton_pattern=skeleton_pattern,
            content_material=content_material,
            topic=user_request.topic,
            persona=user_request.persona,
            additional_text=user_request.additional_text,
            target_duration_seconds=user_request.target_duration_seconds
        )

        # Step 6: Polish script
        polished_script = await self.script_polisher.polish_script(
            draft_script=draft_script,
            topic=user_request.topic
        )

        # Step 7: Generate visual outlay
        visual_outlay = await self.visual_outlay_generator.generate_visual_outlay(
            polished_script=polished_script,
            topic=user_request.topic
        )

        # Step 8: Inject directing instructions
        final_plan = await self.direction_injector.inject_directions(
            polished_script=polished_script,
            topic=user_request.topic,
            visual_outlay=visual_outlay
        )

        # Update final plan with visual outlay
        final_plan.visual_outlay = visual_outlay

        return final_plan

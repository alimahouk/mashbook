--
-- PostgreSQL database dump
--

-- Dumped from database version 14.9 (Homebrew)
-- Dumped by pg_dump version 15.4

-- Started on 2023-10-05 15:58:47 +04

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 5 (class 2615 OID 2200)
-- Name: public; Type: SCHEMA; Schema: -; Owner: mahouk
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO mahouk;

--
-- TOC entry 2 (class 3079 OID 36280)
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- TOC entry 3640 (class 0 OID 0)
-- Dependencies: 2
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 214 (class 1259 OID 36272)
-- Name: chat_; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_ (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    creation_timestamp timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    user_id bigint NOT NULL,
    model_id smallint NOT NULL,
    topic character varying,
    fork_message_id uuid
);


ALTER TABLE public.chat_ OWNER TO postgres;

--
-- TOC entry 215 (class 1259 OID 36302)
-- Name: chat_message_; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_message_ (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    creation_timestamp timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    chat_id uuid NOT NULL,
    sender_id bigint,
    sender_role character varying NOT NULL,
    content_html character varying,
    content_md character varying
);


ALTER TABLE public.chat_message_ OWNER TO postgres;

--
-- TOC entry 213 (class 1259 OID 36262)
-- Name: model_; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.model_ (
    id smallint NOT NULL,
    name character varying NOT NULL,
    display_name character varying NOT NULL
);


ALTER TABLE public.model_ OWNER TO postgres;

--
-- TOC entry 212 (class 1259 OID 36261)
-- Name: model__id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.model_ ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.model__id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 211 (class 1259 OID 36230)
-- Name: user_; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_ (
    id bigint NOT NULL,
    email_address character varying NOT NULL,
    password character(64) NOT NULL,
    salt character(64) NOT NULL,
    name character varying,
    creation_timestamp timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.user_ OWNER TO postgres;

--
-- TOC entry 210 (class 1259 OID 36229)
-- Name: user__id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.user_ ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.user__id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 216 (class 1259 OID 36325)
-- Name: user_session_; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_session_ (
    id character(64) NOT NULL,
    creation_timestamp timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    user_id bigint NOT NULL,
    ip_address inet,
    mac_address macaddr,
    last_activity timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    location character varying
);


ALTER TABLE public.user_session_ OWNER TO postgres;

--
-- TOC entry 3486 (class 2606 OID 36308)
-- Name: chat_message_ chat_message_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_message_
    ADD CONSTRAINT chat_message_pkey PRIMARY KEY (id);


--
-- TOC entry 3484 (class 2606 OID 36279)
-- Name: chat_ chat_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_
    ADD CONSTRAINT chat_pkey PRIMARY KEY (id);


--
-- TOC entry 3482 (class 2606 OID 36268)
-- Name: model_ model__pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.model_
    ADD CONSTRAINT model__pkey PRIMARY KEY (id);


--
-- TOC entry 3480 (class 2606 OID 36236)
-- Name: user_ user__pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_
    ADD CONSTRAINT user__pkey PRIMARY KEY (id);


--
-- TOC entry 3488 (class 2606 OID 36331)
-- Name: user_session_ user_session_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_session_
    ADD CONSTRAINT user_session_pkey PRIMARY KEY (id);


--
-- TOC entry 3489 (class 2606 OID 36362)
-- Name: chat_ chat_fork_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_
    ADD CONSTRAINT chat_fork_message_id_fkey FOREIGN KEY (fork_message_id) REFERENCES public.chat_message_(id) ON UPDATE CASCADE ON DELETE SET NULL NOT VALID;


--
-- TOC entry 3492 (class 2606 OID 36311)
-- Name: chat_message_ chat_message_chat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_message_
    ADD CONSTRAINT chat_message_chat_id_fkey FOREIGN KEY (chat_id) REFERENCES public.chat_(id) ON UPDATE CASCADE ON DELETE CASCADE NOT VALID;


--
-- TOC entry 3493 (class 2606 OID 36316)
-- Name: chat_message_ chat_message_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_message_
    ADD CONSTRAINT chat_message_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.user_(id) ON UPDATE CASCADE NOT VALID;


--
-- TOC entry 3490 (class 2606 OID 36292)
-- Name: chat_ chat_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_
    ADD CONSTRAINT chat_model_id_fkey FOREIGN KEY (model_id) REFERENCES public.model_(id) ON UPDATE CASCADE ON DELETE SET NULL NOT VALID;


--
-- TOC entry 3491 (class 2606 OID 36297)
-- Name: chat_ chat_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_
    ADD CONSTRAINT chat_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_(id) ON UPDATE CASCADE ON DELETE CASCADE NOT VALID;


--
-- TOC entry 3494 (class 2606 OID 36340)
-- Name: user_session_ user_session_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_session_
    ADD CONSTRAINT user_session_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_(id) ON UPDATE CASCADE ON DELETE CASCADE NOT VALID;


--
-- TOC entry 3639 (class 0 OID 0)
-- Dependencies: 5
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: mahouk
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;


-- Completed on 2023-10-05 15:58:47 +04

--
-- PostgreSQL database dump complete
--

